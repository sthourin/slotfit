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
            bucket["total_sets"] += 1
            bucket["total_reps"] += reps or 0
            bucket["total_volume"] += load * (reps or 0)

    return dict(totals)
