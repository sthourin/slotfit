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
    # (weight, reps, time_seconds); legacy workout_sets has no duration column.
    assert history[0]["sets"] == [(110.0, 10, None)]
    assert history[1]["sets"] == [(100.0, 10, None), (100.0, 9, None)]


@pytest.mark.asyncio
async def test_exercise_set_history_includes_time_seconds(test_db):
    """Time-based work must survive into history or progression cannot see it.

    Regression guard: the query never selected time_seconds, so a rower logged
    in seconds arrived at the progression math as (None, None) and had a rep
    target invented for it from thin air.
    """
    user, ex, hp = await _setup(test_db)
    rower = Exercise(name="Test Rower", movement_pattern_1="Conditioning", mechanics="Compound")
    test_db.add(rower)
    await test_db.flush()

    session = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                              started_at=datetime(2026, 8, 1, 9), completed_at=datetime(2026, 8, 1, 10))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=rower.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, time_seconds=300))
    entry.sets.append(EntrySet(set_number=2, time_seconds=240))
    rnd.entries.append(entry)
    session.rounds.append(rnd)
    test_db.add(session)
    await test_db.commit()

    history = await exercise_set_history(test_db, user.id, rower.id)
    assert len(history) == 1
    assert history[0]["sets"] == [(None, None, 300), (None, None, 240)]


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


@pytest.mark.asyncio
async def test_times_performed_counts_sessions_not_rows(test_db):
    """An exercise repeated across multiple rounds/entries of ONE session
    must count as 1, not once per row - regression for undercounting bug
    that would wrongly promote a same-session repeat in staple backfill.
    """
    user, ex, hp = await _setup(test_db)

    # New-schema completed session with the exercise repeated in TWO rounds
    new = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                          started_at=datetime(2026, 2, 1, 9), completed_at=datetime(2026, 2, 1, 10))
    rnd1 = SupersetRound(order=1)
    entry1 = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry1.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd1.entries.append(entry1)
    rnd2 = SupersetRound(order=2)
    entry2 = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry2.sets.append(EntrySet(set_number=1, weight=115.0, reps=8))
    rnd2.entries.append(entry2)
    new.rounds.append(rnd1)
    new.rounds.append(rnd2)
    test_db.add(new)

    # Legacy completed session with the exercise repeated as TWO WorkoutExercises
    legacy = WorkoutSession(user_id=user.id, state=WorkoutState.COMPLETED,
                            started_at=datetime(2026, 1, 5, 9), completed_at=datetime(2026, 1, 5, 10))
    we1 = WorkoutExercise(exercise_id=ex.id)
    we1.sets.append(WorkoutSet(set_number=1, weight=100.0, reps=10))
    we2 = WorkoutExercise(exercise_id=ex.id)
    we2.sets.append(WorkoutSet(set_number=1, weight=95.0, reps=12))
    legacy.exercises.append(we1)
    legacy.exercises.append(we2)
    test_db.add(legacy)

    await test_db.commit()

    counts = await times_performed_map(test_db, user.id)
    # 1 legacy session + 1 new session = 2, NOT 4 rows
    assert counts[ex.id] == 2


@pytest.mark.asyncio
async def test_exercise_set_history_distinguishes_identical_timestamps(test_db):
    """Two distinct sessions sharing an identical completed_at must not be
    merged into a single performance - regression for the by-timestamp
    grouping bug that undercounted len(history) and interleaved sets.
    """
    user, ex, hp = await _setup(test_db)
    same_time = datetime(2026, 2, 1, 10)

    new1 = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                           started_at=datetime(2026, 2, 1, 9), completed_at=same_time)
    rnd1 = SupersetRound(order=1)
    entry1 = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry1.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd1.entries.append(entry1)
    new1.rounds.append(rnd1)
    test_db.add(new1)

    new2 = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                           started_at=datetime(2026, 2, 2, 9), completed_at=same_time)
    rnd2 = SupersetRound(order=1)
    entry2 = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry2.sets.append(EntrySet(set_number=1, weight=120.0, reps=8))
    rnd2.entries.append(entry2)
    new2.rounds.append(rnd2)
    test_db.add(new2)

    await test_db.commit()

    history = await exercise_set_history(test_db, user.id, ex.id)
    assert len(history) == 2
    sets_seen = {tuple(h["sets"]) for h in history}
    assert sets_seen == {((110.0, 10, None),), ((120.0, 8, None),)}
    assert all(h["performed_at"] == same_time for h in history)


@pytest.mark.asyncio
async def test_none_completed_at_is_consistent_across_maps(test_db):
    """A COMPLETED session with completed_at=None must be invisible to both
    map functions identically - regression for the two functions disagreeing
    on None handling.
    """
    user, ex, hp = await _setup(test_db)
    new = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                          started_at=datetime(2026, 2, 1, 9), completed_at=None)
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=ex.id, pattern_id=hp.id)
    entry.sets.append(EntrySet(set_number=1, weight=110.0, reps=10))
    rnd.entries.append(entry)
    new.rounds.append(rnd)
    test_db.add(new)
    await test_db.commit()

    assert await last_performed_map(test_db, user.id, [ex.id]) == {}
    assert (await times_performed_map(test_db, user.id)).get(ex.id) is None
