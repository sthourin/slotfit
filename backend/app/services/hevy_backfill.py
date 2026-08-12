"""Backfill SlotFit history from a local Hevy export.

Hevy stores every weight in kilograms and converts for display. This user's
history is unambiguous about which unit he actually trains in: across 3,932
weighted sets the kilogram values are ugly (40.82, 18.14, 36.29) and the pound
values are exact (90, 40, 80). So the boundary converts kg to lbs once, on the
way in, and everything downstream stays in pounds and stays unitless - matching
`DEFAULT_INCREMENT = 5.0`, which is a plate jump in pounds and would be an
absurd one in kilograms.

Convert once, here. Never round-trip: repeated conversion accumulates error and
turns a clean 90 into 89.9.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bodyweight_reading import BodyweightReading
from app.models.exercise import Exercise
from app.models.user import User
from app.services.hevy_import import variant_name_for
from app.models.workout import (
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
    WorkoutState,
)

KG_TO_LBS = 2.20462

# Marks rows this backfill created, so they are distinguishable from anything
# the user typed and from a future Health Connect sync.
HEVY_SOURCE = "hevy"


def kg_to_lbs(kg: float | None) -> float | None:
    """Kilograms to pounds, rounded to one decimal.

    One decimal is enough to land Hevy's stored 40.8233 exactly on 90.0 while
    keeping the number readable.
    """
    if kg is None:
        return None
    return round(kg * KG_TO_LBS, 1)


async def backfill_bodyweight(
    db: AsyncSession, user: User, measurements: list[dict]
) -> tuple[int, int]:
    """Import dated bodyweight readings. Returns (created, skipped).

    Idempotent through the (user, recorded_at, source) unique constraint: a
    second run updates the weight in place rather than duplicating the reading.
    """
    existing = {
        recorded_at: reading_id
        for reading_id, recorded_at in (
            await db.execute(
                select(BodyweightReading.id, BodyweightReading.recorded_at).where(
                    BodyweightReading.user_id == user.id,
                    BodyweightReading.source == HEVY_SOURCE,
                )
            )
        ).all()
    }

    created = skipped = 0
    for entry in measurements:
        weight_kg = entry.get("weight_kg")
        raw_date = entry.get("date")
        if weight_kg is None or not raw_date:
            skipped += 1
            continue
        recorded_at = datetime.fromisoformat(raw_date)
        if recorded_at in existing:
            skipped += 1
            continue
        db.add(
            BodyweightReading(
                user_id=user.id,
                weight=kg_to_lbs(weight_kg),
                recorded_at=recorded_at,
                source=HEVY_SOURCE,
            )
        )
        existing[recorded_at] = -1
        created += 1

    await db.commit()
    return created, skipped


async def backfill_workouts(
    db: AsyncSession, user: User, workouts: list[dict], title_to_exercise: dict[str, int]
) -> tuple[int, int, int]:
    """Import completed workouts into the legacy tables. Returns (sessions, sets, unmapped_sets).

    The legacy tables are the right home: their shape (session -> exercises ->
    sets) is exactly Hevy's, and `history_service` already unions them with the
    training-session tables, so importing here lights up rotation, progression
    targets, strength trends and volume at once without a schema change.

    Idempotent on (user, started_at). Hevy start times are distinct per workout,
    and re-running must not double a user's training history.

    Titles absent from `title_to_exercise` are counted and skipped rather than
    guessed at. The mapping was reviewed by hand; inventing matches for the
    unreviewed tail would put wrong exercises into three years of history.
    """
    existing_starts = {
        started_at
        for (started_at,) in (
            await db.execute(
                select(WorkoutSession.started_at).where(WorkoutSession.user_id == user.id)
            )
        ).all()
    }

    sessions_created = sets_created = unmapped_sets = 0

    for workout in workouts:
        raw_start = (workout.get("start_time") or "").replace("Z", "+00:00")
        try:
            started_at = datetime.fromisoformat(raw_start).replace(tzinfo=None)
        except ValueError:
            continue
        if started_at in existing_starts:
            continue

        raw_end = (workout.get("end_time") or "").replace("Z", "+00:00")
        try:
            completed_at = datetime.fromisoformat(raw_end).replace(tzinfo=None)
        except ValueError:
            completed_at = started_at

        session = WorkoutSession(
            user_id=user.id,
            state=WorkoutState.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
        )
        session_sets = 0

        for entry in workout.get("exercises") or []:
            exercise_id = title_to_exercise.get(entry.get("title"))
            raw_sets = entry.get("sets") or []
            if exercise_id is None:
                unmapped_sets += len(raw_sets)
                continue
            workout_exercise = WorkoutExercise(
                exercise_id=exercise_id, started_at=started_at
            )
            for number, raw in enumerate(raw_sets, start=1):
                workout_exercise.sets.append(
                    WorkoutSet(
                        set_number=number,
                        weight=kg_to_lbs(raw.get("weight_kg")),
                        reps=raw.get("reps"),
                    )
                )
                session_sets += 1
            session.exercises.append(workout_exercise)

        if session_sets == 0:
            # Nothing resolvable in this workout; an empty session would only
            # pollute counts and history.
            continue

        db.add(session)
        existing_starts.add(started_at)
        sessions_created += 1
        sets_created += session_sets

    await db.commit()
    return sessions_created, sets_created, unmapped_sets


def title_map_from_document(document: dict, exercises_by_name: dict[str, int]) -> dict[str, int]:
    """Hevy title -> SlotFit exercise id, from the reviewed mapping document.

    The map resolves an entry three ways, and all three must be honoured or the
    interval variants drop out - they are exactly the entries that use the third:

      slotfit: <name>                          an existing exercise
      create: {name: ...}                      a new exercise, named directly
      create: {variant_of: ..., variant_type:}  a variant, named by convention
    """
    mapping: dict[str, int] = {}
    for entry in document.get("exercises") or []:
        title = entry.get("hevy")
        selection = entry.get("slotfit")
        if not title or str(selection) == "SKIP":
            continue

        name = None
        if isinstance(selection, str) and selection:
            name = selection
        else:
            create = entry.get("create") or {}
            if create.get("name"):
                name = create["name"]
            elif create.get("variant_of") and create.get("variant_type"):
                name = variant_name_for(create["variant_of"], create["variant_type"])

        if not name:
            continue
        exercise_id = exercises_by_name.get(name)
        if exercise_id is not None:
            mapping[title] = exercise_id
    return mapping


async def exercises_by_name(db: AsyncSession) -> dict[str, int]:
    rows = (await db.execute(select(Exercise.name, Exercise.id))).all()
    return {name: exercise_id for name, exercise_id in rows}
