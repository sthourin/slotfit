"""Tests for live weekly volume computation."""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import insert

from app.models import (
    BodyweightReading,
    Equipment,
    EntrySet,
    Exercise,
    MovementPattern,
    MuscleGroup,
    RoundEntry,
    SessionState,
    SupersetRound,
    TrainingSession,
    User,
    WorkoutExercise,
    WorkoutSession,
    WorkoutSet,
)
from app.models.exercise import exercise_muscle_groups
from app.models.workout import WorkoutState
from app.services.pattern_taxonomy import seed_movement_patterns
from app.services.volume_service import weekly_volume_by_muscle_group


def _monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def _at(d: date, hour: int = 9) -> datetime:
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=hour)


async def _link(db, exercise_id: int, muscle_group_id: int, role: str) -> None:
    await db.execute(
        insert(exercise_muscle_groups).values(
            exercise_id=exercise_id, muscle_group_id=muscle_group_id, role=role
        )
    )


async def _training_session(db, user, exercise, pattern, when, sets):
    """sets: list of (weight, reps)."""
    s = TrainingSession(
        user_id=user.id, state=SessionState.COMPLETED, started_at=when, completed_at=when
    )
    r = SupersetRound(order=1)
    e = RoundEntry(position=1, exercise_id=exercise.id, pattern_id=pattern.id)
    for n, (weight, reps) in enumerate(sets, start=1):
        e.sets.append(EntrySet(set_number=n, weight=weight, reps=reps))
    r.entries.append(e)
    s.rounds.append(r)
    db.add(s)
    await db.commit()


async def _fixture(db, device="vol-0001"):
    """Mirrors the real catalogue's shape for a bench press.

    The four roles are hierarchy levels over the same movement, not a list of
    muscles: target "Chest" (level 1), prime mover "Pectoralis Major" (level 2),
    then the secondary and tertiary contributors.
    """
    await seed_movement_patterns(db)
    user = User(device_id=device)
    chest = MuscleGroup(name="Chest", level=1)
    pecs = MuscleGroup(name="Pectoralis Major", level=2)
    triceps = MuscleGroup(name="Triceps Brachii", level=3)
    barbell = Equipment(name="Barbell")
    db.add_all([user, chest, pecs, triceps, barbell])
    await db.flush()
    bench = Exercise(
        name="Volume Bench Press", movement_pattern_1="Horizontal Push",
        mechanics="Compound", primary_equipment_id=barbell.id,
    )
    db.add(bench)
    await db.flush()
    await _link(db, bench.id, chest.id, "target")
    await _link(db, bench.id, pecs.id, "prime_mover")
    await _link(db, bench.id, triceps.id, "secondary")
    from sqlalchemy import select

    pattern = (
        await db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_push"))
    ).scalar_one()
    await db.commit()
    return user, bench, chest, pecs, triceps, pattern


@pytest.mark.asyncio
async def test_counts_sets_reps_and_tonnage_from_training_sessions(test_db):
    """The tables sessions are actually logged into must be counted.

    Regression guard: volume read a weekly_volume aggregate table that nothing
    has ever written, so every number on the analytics page was zero.
    """
    user, bench, chest, _pecs, _triceps, pattern = await _fixture(test_db)
    week = _monday()
    await _training_session(
        test_db, user, bench, pattern, _at(week + timedelta(days=1)),
        [(100.0, 10), (100.0, 8)],
    )

    volume = await weekly_volume_by_muscle_group(test_db, user.id, week)
    assert volume[chest.id]["total_sets"] == 2
    assert volume[chest.id]["total_reps"] == 18
    assert volume[chest.id]["total_volume"] == pytest.approx(1800.0)


@pytest.mark.asyncio
async def test_only_the_target_level_is_counted(test_db):
    """The roles are zoom levels on one movement, not separate muscles worked.

    Crediting the prime mover as well would report every bench press set twice -
    once as "Chest" and once as "Pectoralis Major".
    """
    user, bench, chest, pecs, triceps, pattern = await _fixture(test_db)
    week = _monday()
    await _training_session(
        test_db, user, bench, pattern, _at(week + timedelta(days=1)), [(100.0, 10)]
    )

    volume = await weekly_volume_by_muscle_group(test_db, user.id, week)
    assert volume[chest.id]["total_sets"] == 1
    assert pecs.id not in volume
    assert triceps.id not in volume


@pytest.mark.asyncio
async def test_other_weeks_are_excluded(test_db):
    user, bench, chest, _pecs, _triceps, pattern = await _fixture(test_db)
    week = _monday()
    await _training_session(
        test_db, user, bench, pattern, _at(week - timedelta(days=3)), [(100.0, 10)]
    )
    await _training_session(
        test_db, user, bench, pattern, _at(week + timedelta(days=8)), [(100.0, 10)]
    )

    assert await weekly_volume_by_muscle_group(test_db, user.id, week) == {}


@pytest.mark.asyncio
async def test_incomplete_sessions_do_not_count(test_db):
    user, bench, chest, _pecs, _triceps, pattern = await _fixture(test_db)
    week = _monday()
    when = _at(week + timedelta(days=1))
    s = TrainingSession(user_id=user.id, state=SessionState.ACTIVE, started_at=when)
    r = SupersetRound(order=1)
    e = RoundEntry(position=1, exercise_id=bench.id, pattern_id=pattern.id)
    e.sets.append(EntrySet(set_number=1, weight=100.0, reps=10))
    r.entries.append(e)
    s.rounds.append(r)
    test_db.add(s)
    await test_db.commit()

    assert await weekly_volume_by_muscle_group(test_db, user.id, week) == {}


@pytest.mark.asyncio
async def test_legacy_workouts_still_count(test_db):
    """Three years of imported history must not vanish from the chart."""
    user, bench, chest, _pecs, _triceps, _pattern = await _fixture(test_db)
    week = _monday()
    when = _at(week + timedelta(days=1))
    legacy = WorkoutSession(
        user_id=user.id, state=WorkoutState.COMPLETED, started_at=when, completed_at=when
    )
    we = WorkoutExercise(exercise_id=bench.id)
    we.sets.append(WorkoutSet(set_number=1, weight=100.0, reps=10))
    legacy.exercises.append(we)
    test_db.add(legacy)
    await test_db.commit()

    volume = await weekly_volume_by_muscle_group(test_db, user.id, week)
    assert volume[chest.id]["total_sets"] == 1
    assert volume[chest.id]["total_volume"] == pytest.approx(1000.0)


@pytest.mark.asyncio
async def test_bodyweight_work_counts_via_leverage(test_db):
    """A session of push-ups is not zero tonnage."""
    await seed_movement_patterns(test_db)
    user = User(device_id="vol-bw-0001")
    chest = MuscleGroup(name="Chest", level=1)
    bodyweight = Equipment(name="Bodyweight")
    test_db.add_all([user, chest, bodyweight])
    await test_db.flush()
    push_up = Exercise(
        name="Volume Push Up", movement_pattern_1="Horizontal Push", mechanics="Compound",
        primary_equipment_id=bodyweight.id, bodyweight_fraction=0.64,
    )
    test_db.add(push_up)
    await test_db.flush()
    await _link(test_db, push_up.id, chest.id, "target")
    from sqlalchemy import select

    pattern = (
        await test_db.execute(
            select(MovementPattern).where(MovementPattern.slug == "horizontal_push")
        )
    ).scalar_one()
    week = _monday()
    test_db.add(BodyweightReading(
        user_id=user.id, weight=200.0, recorded_at=_at(week - timedelta(days=7)), source="manual"
    ))
    await test_db.commit()

    await _training_session(
        test_db, user, push_up, pattern, _at(week + timedelta(days=1)), [(None, 10)]
    )

    volume = await weekly_volume_by_muscle_group(test_db, user.id, week)
    # 200 * 0.64 = 128 per rep-set -> 1280 for 10 reps
    assert volume[chest.id]["total_volume"] == pytest.approx(1280.0)
    assert volume[chest.id]["total_sets"] == 1


@pytest.mark.asyncio
async def test_bodyweight_work_with_no_reading_still_counts_sets(test_db):
    """Sets and reps are known even when the load is not.

    Dropping the set entirely would understate how much work was done, which is
    the opposite of the problem tonnage is meant to measure.
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="vol-nobw-0001")
    chest = MuscleGroup(name="Chest", level=1)
    bodyweight = Equipment(name="Bodyweight")
    test_db.add_all([user, chest, bodyweight])
    await test_db.flush()
    push_up = Exercise(
        name="Volume Push Up", movement_pattern_1="Horizontal Push", mechanics="Compound",
        primary_equipment_id=bodyweight.id, bodyweight_fraction=0.64,
    )
    test_db.add(push_up)
    await test_db.flush()
    await _link(test_db, push_up.id, chest.id, "target")
    from sqlalchemy import select

    pattern = (
        await test_db.execute(
            select(MovementPattern).where(MovementPattern.slug == "horizontal_push")
        )
    ).scalar_one()
    await test_db.commit()

    week = _monday()
    await _training_session(
        test_db, user, push_up, pattern, _at(week + timedelta(days=1)), [(None, 10)]
    )

    volume = await weekly_volume_by_muscle_group(test_db, user.id, week)
    assert volume[chest.id]["total_sets"] == 1
    assert volume[chest.id]["total_reps"] == 10
    assert volume[chest.id]["total_volume"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_volume_is_scoped_to_one_user(test_db):
    user, bench, chest, _pecs, _triceps, pattern = await _fixture(test_db)
    other = User(device_id="vol-other-0002")
    test_db.add(other)
    await test_db.flush()
    week = _monday()
    await _training_session(
        test_db, user, bench, pattern, _at(week + timedelta(days=1)), [(100.0, 10)]
    )

    assert await weekly_volume_by_muscle_group(test_db, other.id, week) == {}
