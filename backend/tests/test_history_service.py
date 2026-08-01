"""Tests for the unified history service (legacy + new tables)"""
import pytest
from datetime import datetime

from app.models import (
    User, Exercise, MovementPattern,
    WorkoutSession, WorkoutExercise, WorkoutSet,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.models.workout import WorkoutState
from app.services.pattern_taxonomy import seed_movement_patterns
from app.services.history_service import (
    last_performed_map, times_performed_map, exercise_set_history,
)
from sqlalchemy import select


async def _setup(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    ex = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, ex])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    return user, ex, result.scalar_one()


@pytest.mark.asyncio
async def test_history_spans_legacy_and_new(test_db):
    user, ex, hp = await _setup(test_db)

    # Legacy completed workout on Jan 5
    legacy = WorkoutSession(user_id=user.id, state=WorkoutState.COMPLETED,
                            started_at=datetime(2026, 1, 5, 9), completed_at=datetime(2026, 1, 5, 10))
    we = WorkoutExercise(exercise_id=ex.id)
    we.sets.append(WorkoutSet(set_number=1, weight=100.0, reps=10))
    we.sets.append(WorkoutSet(set_number=2, weight=100.0, reps=9))
    legacy.exercises.append(we)
    test_db.add(legacy)

    # New completed session on Feb 1
    new = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                          started_at=datetime(2026, 2, 1, 9), completed_at=datetime(2026, 2, 1, 10))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd.entries.append(entry)
    new.rounds.append(rnd)
    test_db.add(new)
    await test_db.commit()

    last = await last_performed_map(test_db, user.id, [ex.id])
    assert last[ex.id] == datetime(2026, 2, 1, 10)  # newer of the two

    counts = await times_performed_map(test_db, user.id)
    assert counts[ex.id] == 2

    history = await exercise_set_history(test_db, user.id, ex.id)
    assert len(history) == 2
    assert history[0]["performed_at"] == datetime(2026, 2, 1, 10)  # newest first
    assert history[0]["sets"] == [(110.0, 10)]
    assert history[1]["sets"] == [(100.0, 10), (100.0, 9)]


@pytest.mark.asyncio
async def test_incomplete_sessions_are_ignored(test_db):
    user, ex, hp = await _setup(test_db)
    active = TrainingSession(user_id=user.id, state=SessionState.ACTIVE, started_at=datetime(2026, 3, 1, 9))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd.entries.append(entry)
    active.rounds.append(rnd)
    test_db.add(active)
    await test_db.commit()

    assert await last_performed_map(test_db, user.id, [ex.id]) == {}
    assert (await times_performed_map(test_db, user.id)).get(ex.id) is None
