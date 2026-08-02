"""Tests for the staple backfill script (backend/scripts/backfill_staples.py)."""

import pytest
from datetime import datetime

from sqlalchemy import select

from app.models import (
    User,
    Exercise,
    MovementPattern,
    StapleExercise,
    ExercisePatternMap,
    WorkoutSession,
    WorkoutExercise,
    WorkoutSet,
    TrainingSession,
    SupersetRound,
    RoundEntry,
    EntrySet,
    SessionState,
)
from app.models.workout import WorkoutState
from app.services.pattern_taxonomy import (
    seed_movement_patterns,
    seed_exercise_pattern_map,
)
from scripts.backfill_staples import backfill_user


async def _make_user_and_exercise(test_db, device_id: str, exercise_name: str):
    """Seed the pattern taxonomy and create one user + one purpose-built compound exercise.

    Uses explicit movement_pattern_1/mechanics ("Horizontal Pull" / "Compound")
    so the exercise classifies to the horizontal_pull pattern rather than the
    neutral "isolation" fallback that tests/seed_data.py exercises land on.
    Returns (user, exercise).
    """
    await seed_movement_patterns(test_db)
    user = User(device_id=device_id)
    ex = Exercise(
        name=exercise_name, movement_pattern_1="Horizontal Pull", mechanics="Compound"
    )
    test_db.add_all([user, ex])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    return user, ex


def _add_completed_legacy_session(
    test_db, user_id: int, exercise_id: int, day: int, rounds: int = 1
):
    """Add one COMPLETED legacy WorkoutSession performing exercise_id.

    `rounds` controls how many WorkoutExercise rows (not sessions) reference
    the exercise within this single session - used to prove that repeats
    within one session count as one session, not one per row.
    """
    session = WorkoutSession(
        user_id=user_id,
        state=WorkoutState.COMPLETED,
        started_at=datetime(2026, 1, day, 9),
        completed_at=datetime(2026, 1, day, 10),
    )
    for i in range(rounds):
        we = WorkoutExercise(exercise_id=exercise_id)
        we.sets.append(WorkoutSet(set_number=1, weight=100.0, reps=10))
        session.exercises.append(we)
    test_db.add(session)


def _add_completed_new_session(
    test_db, user_id: int, exercise_id: int, pattern_id: int, day: int, rounds: int = 1
):
    """Add one COMPLETED new-schema TrainingSession performing exercise_id.

    `rounds` controls how many SupersetRound/RoundEntry pairs reference the
    exercise within this single session - used to prove that repeats within
    one session count as one session, not one per round.
    """
    session = TrainingSession(
        user_id=user_id,
        state=SessionState.COMPLETED,
        started_at=datetime(2026, 2, day, 9),
        completed_at=datetime(2026, 2, day, 10),
    )
    for i in range(rounds):
        rnd = SupersetRound(order=i + 1)
        entry = RoundEntry(position=1, exercise_id=exercise_id, pattern_id=pattern_id)
        entry.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
        rnd.entries.append(entry)
        session.rounds.append(rnd)
    test_db.add(session)


@pytest.mark.asyncio
async def test_exercise_at_threshold_becomes_staple(test_db):
    """An exercise performed in exactly 3 completed sessions becomes a staple."""
    user, ex = await _make_user_and_exercise(
        test_db, "device-at-threshold", "Seated Cable Row"
    )
    _add_completed_legacy_session(test_db, user.id, ex.id, day=1)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=2)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=3)
    await test_db.commit()

    created = await backfill_user(test_db, user)
    assert created == 1

    result = await test_db.execute(
        select(StapleExercise).where(
            StapleExercise.user_id == user.id, StapleExercise.exercise_id == ex.id
        )
    )
    staple = result.scalar_one()
    mapping = (
        await test_db.execute(
            select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == ex.id)
        )
    ).scalar_one()
    assert staple.pattern_id == mapping.pattern_id


@pytest.mark.asyncio
async def test_exercise_below_threshold_is_not_staple(test_db):
    """An exercise performed in only 2 completed sessions does NOT become a staple."""
    user, ex = await _make_user_and_exercise(
        test_db, "device-below-threshold", "Barbell Row"
    )
    _add_completed_legacy_session(test_db, user.id, ex.id, day=1)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=2)
    await test_db.commit()

    created = await backfill_user(test_db, user)
    assert created == 0

    result = await test_db.execute(
        select(StapleExercise).where(
            StapleExercise.user_id == user.id, StapleExercise.exercise_id == ex.id
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_repeats_within_one_session_do_not_cross_threshold(test_db):
    """An exercise appearing in two rounds of a SINGLE completed session counts
    as 1 session, not 2 - regression for the row-vs-session counting bug.

    Two single-round sessions plus one two-round session = 3 rows but only
    2 distinct sessions, so this must NOT become a staple.
    """
    user, ex = await _make_user_and_exercise(
        test_db, "device-single-session-repeat", "Lat Pulldown"
    )
    mapping = (
        await test_db.execute(
            select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == ex.id)
        )
    ).scalar_one()

    _add_completed_new_session(
        test_db, user.id, ex.id, mapping.pattern_id, day=1, rounds=1
    )
    _add_completed_new_session(
        test_db, user.id, ex.id, mapping.pattern_id, day=2, rounds=2
    )  # 1 session, 2 rows
    await test_db.commit()

    created = await backfill_user(test_db, user)
    assert created == 0

    result = await test_db.execute(
        select(StapleExercise).where(
            StapleExercise.user_id == user.id, StapleExercise.exercise_id == ex.id
        )
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_backfill_user_is_idempotent(test_db):
    """Running backfill_user twice creates 0 additional staples the second time."""
    user, ex = await _make_user_and_exercise(
        test_db, "device-idempotent", "Chest Supported Row"
    )
    _add_completed_legacy_session(test_db, user.id, ex.id, day=1)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=2)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=3)
    await test_db.commit()

    first_run = await backfill_user(test_db, user)
    assert first_run == 1

    second_run = await backfill_user(test_db, user)
    assert second_run == 0

    result = await test_db.execute(
        select(StapleExercise).where(
            StapleExercise.user_id == user.id, StapleExercise.exercise_id == ex.id
        )
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_exercise_without_pattern_mapping_is_skipped(test_db):
    """An exercise with no ExercisePatternMap row is skipped without raising."""
    await seed_movement_patterns(test_db)
    user = User(device_id="device-no-mapping")
    ex = Exercise(
        name="Unmapped Exercise",
        movement_pattern_1="Horizontal Pull",
        mechanics="Compound",
    )
    test_db.add_all([user, ex])
    await test_db.flush()
    # Deliberately do NOT call seed_exercise_pattern_map - ex has no mapping row.

    _add_completed_legacy_session(test_db, user.id, ex.id, day=1)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=2)
    _add_completed_legacy_session(test_db, user.id, ex.id, day=3)
    await test_db.commit()

    created = await backfill_user(test_db, user)
    assert created == 0

    result = await test_db.execute(
        select(StapleExercise).where(
            StapleExercise.user_id == user.id, StapleExercise.exercise_id == ex.id
        )
    )
    assert result.scalar_one_or_none() is None
