"""Weekly training volume, computed live from logged sets.

This deliberately does not read the `weekly_volume` table. That table is a
denormalised aggregate that nothing has ever written, so every volume figure
the app reported was zero regardless of how much was logged. Computing from the
sets themselves cannot drift out of sync, and at one user's data volume the
cost is irrelevant.

Both generations of history count: the legacy workout tables hold three years
of imported Hevy history, and the training-session tables hold everything
logged since.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import Exercise
from app.models.training_session import (
    EntrySet,
    RoundEntry,
    SessionState,
    SupersetRound,
    TrainingSession,
)
from app.models.workout import WorkoutExercise, WorkoutSession, WorkoutSet, WorkoutState
from app.services.bodyweight_service import (
    bodyweight_timeline,
    effective_load,
    resolve_bodyweight,
)
from app.services.exercise_helpers import bodyweight_equipment_id

# The role a set is credited to. The four roles are levels of a hierarchy, not
# a ranked list of muscles: a bench press has target "Chest" (level 1) and
# prime mover "Pectoralis Major" (level 2) - the same work at two zoom levels.
# Counting both would report every set twice, and adding the secondary and
# tertiary contributors on top would inflate the chart into noise. `target` is
# the level a training log is read at: "Chest: 12 sets this week".
VOLUME_ROLE = "target"


async def weekly_volume_by_muscle_group(
    db: AsyncSession, user_id: int, week_start: date
) -> dict[int, dict]:
    """Volume for the ISO week beginning `week_start` (a Monday).

    Returns {muscle_group_id: {"total_sets", "total_reps", "total_volume"}}.

    Tonnage uses effective load, so bodyweight work contributes rather than
    counting as zero. A bodyweight set with no weigh-in to resolve against
    still contributes its sets and reps - those are known - and simply adds no
    tonnage, since dropping it entirely would understate the work done.
    """
    window_start = datetime.combine(week_start, datetime.min.time())
    window_end = window_start + timedelta(days=7)

    legacy_rows = (
        await db.execute(
            select(WorkoutExercise.exercise_id, WorkoutSet.weight, WorkoutSet.reps,
                   WorkoutSession.completed_at)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.state == WorkoutState.COMPLETED,
                WorkoutSession.completed_at >= window_start,
                WorkoutSession.completed_at < window_end,
            )
        )
    ).all()

    new_rows = (
        await db.execute(
            select(RoundEntry.exercise_id, EntrySet.weight, EntrySet.reps,
                   TrainingSession.completed_at)
            .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
            .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
            .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
            .where(
                TrainingSession.user_id == user_id,
                TrainingSession.state == SessionState.COMPLETED,
                EntrySet.completed == True,  # noqa: E712
                TrainingSession.completed_at >= window_start,
                TrainingSession.completed_at < window_end,
            )
        )
    ).all()

    rows = list(legacy_rows) + list(new_rows)
    if not rows:
        return {}

    # muscle_groups is eager-loaded: a lazy many-to-many access raises on an
    # async session, and these exercises are whatever was logged this week.
    exercises = {
        exercise.id: exercise
        for exercise in (
            await db.execute(
                select(Exercise)
                .where(Exercise.id.in_({exercise_id for exercise_id, _w, _r, _c in rows}))
                .options(selectinload(Exercise.muscle_groups))
            )
        ).scalars().all()
    }

    # Roles live on the association table rather than on MuscleGroup, so they
    # need their own lookup to tell a prime mover from a tertiary contributor.
    role_rows = (
        await db.execute(
            select(
                Exercise.id,
                Exercise.muscle_groups.property.secondary.c.muscle_group_id,
                Exercise.muscle_groups.property.secondary.c.role,
            ).join(
                Exercise.muscle_groups.property.secondary,
                Exercise.muscle_groups.property.secondary.c.exercise_id == Exercise.id,
            ).where(Exercise.id.in_(exercises.keys()))
        )
    ).all()
    primary_by_exercise: dict[int, set[int]] = defaultdict(set)
    for exercise_id, muscle_group_id, role in role_rows:
        if role == VOLUME_ROLE:
            primary_by_exercise[exercise_id].add(muscle_group_id)

    timeline = await bodyweight_timeline(db, user_id)
    bodyweight_id = await bodyweight_equipment_id(db)

    totals: dict[int, dict] = defaultdict(
        lambda: {"total_sets": 0, "total_reps": 0, "total_volume": 0.0}
    )
    for exercise_id, weight, reps, completed_at in rows:
        exercise = exercises.get(exercise_id)
        if exercise is None:
            continue
        bodyweight = resolve_bodyweight(timeline, completed_at) if completed_at else None
        load = effective_load(exercise, weight, bodyweight, bodyweight_id) or 0.0
        for muscle_group_id in primary_by_exercise.get(exercise_id, ()):
            bucket = totals[muscle_group_id]
            # A conditioning set counts here as a set and adds no tonnage. Both
            # halves are deliberate. The set happened and its target muscle is
            # known, so hiding it would understate the week's work. But its
            # tonnage is unrepresentable: `load * reps` with no reps is zero,
            # and the load-distance product that WOULD describe it belongs in
            # `weekly_conditioning` instead. Adding it here would let one 5km
            # ruck at 235lb produce ~1.2M against ~50k for a hard lifting week -
            # the same "inflate the chart into noise" failure documented above
            # for muscle roles, on a different axis.
            bucket["total_sets"] += 1
            bucket["total_reps"] += reps or 0
            bucket["total_volume"] += load * (reps or 0)

    return dict(totals)


async def weekly_conditioning(
    db: AsyncSession, user_id: int, week_start: date
) -> dict:
    """Conditioning work for the ISO week beginning `week_start` (a Monday).

    Deliberately parallel to `weekly_volume_by_muscle_group` rather than folded
    into it. Tonnage answers "how much did you move"; this answers "how far and
    how long", and the two do not share a unit. Reporting them in one number
    would make both unreadable.

    A set counts as conditioning when it records a duration or a distance and no
    reps. That is a property of the set as logged, not of how the exercise is
    currently classified, so re-protocoling an exercise later never rewrites
    what past sets meant - the same reason `RoundEntry.set_protocol` is
    denormalised.

    `load_meters` is effective load x metres, so a ruck is scored for carrying
    its pack while an ergometer - which carries the athlete - contributes none.
    Distance work with no load resolves to 0.0 rather than being dropped: the
    metres are still real.
    """
    window_start = datetime.combine(week_start, datetime.min.time())
    window_end = window_start + timedelta(days=7)

    legacy_rows = (
        await db.execute(
            select(WorkoutExercise.exercise_id, WorkoutSet.weight,
                   WorkoutSet.time_seconds, WorkoutSet.distance_meters,
                   WorkoutSession.completed_at)
            .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
            .join(WorkoutSet, WorkoutSet.workout_exercise_id == WorkoutExercise.id)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.state == WorkoutState.COMPLETED,
                WorkoutSession.completed_at >= window_start,
                WorkoutSession.completed_at < window_end,
                WorkoutSet.reps.is_(None),
            )
        )
    ).all()

    new_rows = (
        await db.execute(
            select(RoundEntry.exercise_id, EntrySet.weight,
                   EntrySet.time_seconds, EntrySet.distance_meters,
                   TrainingSession.completed_at)
            .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
            .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
            .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
            .where(
                TrainingSession.user_id == user_id,
                TrainingSession.state == SessionState.COMPLETED,
                EntrySet.completed == True,  # noqa: E712
                TrainingSession.completed_at >= window_start,
                TrainingSession.completed_at < window_end,
                EntrySet.reps.is_(None),
            )
        )
    ).all()

    rows = [
        row for row in list(legacy_rows) + list(new_rows)
        if row[2] is not None or row[3] is not None
    ]
    if not rows:
        return {
            "total_sets": 0, "total_seconds": 0, "total_meters": 0.0,
            "load_meters": 0.0, "pace_seconds_per_km": None, "by_exercise": [],
        }

    exercises = {
        exercise.id: exercise
        for exercise in (
            await db.execute(
                select(Exercise).where(
                    Exercise.id.in_({exercise_id for exercise_id, *_rest in rows})
                )
            )
        ).scalars().all()
    }

    timeline = await bodyweight_timeline(db, user_id)
    bodyweight_id = await bodyweight_equipment_id(db)

    # `paced_*` accumulate only from sets recording BOTH a duration and a
    # distance. Pace computed from the plain totals is wrong whenever the week
    # mixes the two kinds of conditioning: 600s of distance-less rowing divided
    # into 500m logged on another day reported 24:10 /km for a 2:05 /km effort.
    # A plank contributes seconds and no metres, and must not slow anything down.
    per_exercise: dict[int, dict] = defaultdict(
        lambda: {
            "sets": 0, "seconds": 0, "meters": 0.0, "load_meters": 0.0,
            "paced_seconds": 0, "paced_meters": 0.0,
        }
    )
    for exercise_id, weight, time_seconds, distance, completed_at in rows:
        exercise = exercises.get(exercise_id)
        if exercise is None:
            continue
        bodyweight = resolve_bodyweight(timeline, completed_at) if completed_at else None
        load = effective_load(exercise, weight, bodyweight, bodyweight_id) or 0.0
        bucket = per_exercise[exercise_id]
        bucket["sets"] += 1
        bucket["seconds"] += time_seconds or 0
        bucket["meters"] += distance or 0.0
        bucket["load_meters"] += load * (distance or 0.0)
        if time_seconds and distance:
            bucket["paced_seconds"] += time_seconds
            bucket["paced_meters"] += distance

    by_exercise = []
    for exercise_id, bucket in per_exercise.items():
        reported = {k: v for k, v in bucket.items() if not k.startswith("paced_")}
        by_exercise.append({
            "exercise_id": exercise_id,
            "name": exercises[exercise_id].name,
            "pace_seconds_per_km": _pace(
                bucket["paced_seconds"], bucket["paced_meters"]
            ),
            **reported,
        })
    by_exercise.sort(key=lambda row: (-row["seconds"], row["name"]))

    return {
        "total_sets": sum(b["sets"] for b in per_exercise.values()),
        "total_seconds": sum(b["seconds"] for b in per_exercise.values()),
        "total_meters": sum(b["meters"] for b in per_exercise.values()),
        "load_meters": sum(b["load_meters"] for b in per_exercise.values()),
        "pace_seconds_per_km": _pace(
            sum(b["paced_seconds"] for b in per_exercise.values()),
            sum(b["paced_meters"] for b in per_exercise.values()),
        ),
        "by_exercise": by_exercise,
    }


def _pace(seconds: int, meters: float) -> float | None:
    """Seconds per kilometre, or None when there is nothing to divide.

    Both arguments must come from the same sets. Time without distance has no
    pace - a plank is not slow - so this returns None rather than a misleading
    infinity or zero.
    """
    if not meters or not seconds:
        return None
    return round(seconds / (meters / 1000.0), 1)
