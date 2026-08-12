"""Tests for the Hevy history backfill."""
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import BodyweightReading, Exercise, User, WorkoutSession, WorkoutSet
from app.services.hevy_backfill import (
    backfill_bodyweight,
    backfill_workouts,
    kg_to_lbs,
    title_map_from_document,
)


def test_kg_to_lbs_lands_hevy_values_on_round_pounds():
    """Hevy stores kg; this user's plates are pounds. 40.8233 kg IS 90 lbs."""
    assert kg_to_lbs(40.8233) == 90.0
    assert kg_to_lbs(18.1437) == 40.0
    assert kg_to_lbs(61.235) == 135.0
    assert kg_to_lbs(None) is None


def test_title_map_reads_all_three_resolution_styles():
    """The variant style is the one the interval staples use.

    Regression guard: reading only `slotfit` and `create.name` silently dropped
    all six HIIT variants, which are precisely the entries resolved by
    variant_of/variant_type.
    """
    document = {
        "exercises": [
            {"hevy": "Bench Press (Barbell)", "slotfit": "Barbell Bench Press"},
            {"hevy": "Odd Lift", "create": {"name": "Odd Lift Variant"}},
            {"hevy": "HIIT KB Swings",
             "create": {"variant_of": "Kettlebell Swing", "variant_type": "HIIT AMRAP"}},
            {"hevy": "Rest", "slotfit": "SKIP"},
            {"hevy": "Unresolved", "slotfit": None},
        ]
    }
    mapping = title_map_from_document(
        document,
        {
            "Barbell Bench Press": 7,
            "Odd Lift Variant": 9,
            "Kettlebell Swing (HIIT AMRAP)": 11,
        },
    )
    assert mapping == {
        "Bench Press (Barbell)": 7,
        "Odd Lift": 9,
        "HIIT KB Swings": 11,
    }


@pytest.mark.asyncio
async def test_bodyweight_backfill_converts_and_is_idempotent(test_db):
    user = User(device_id="bf-bw-0001")
    test_db.add(user)
    await test_db.flush()
    measurements = [
        {"date": "2026-05-30", "weight_kg": 100.79},
        {"date": "2026-05-29", "weight_kg": 100.89},
        {"date": "2026-05-28", "weight_kg": None},
    ]

    created, skipped = await backfill_bodyweight(test_db, user, measurements)
    assert created == 2
    assert skipped == 1

    readings = (
        await test_db.execute(
            select(BodyweightReading).where(BodyweightReading.user_id == user.id)
        )
    ).scalars().all()
    assert {r.weight for r in readings} == {222.2, 222.4}
    assert all(r.source == "hevy" for r in readings)

    # Re-running must not duplicate three years of weigh-ins.
    created_again, _ = await backfill_bodyweight(test_db, user, measurements)
    assert created_again == 0
    assert len(
        (
            await test_db.execute(
                select(BodyweightReading).where(BodyweightReading.user_id == user.id)
            )
        ).scalars().all()
    ) == 2


def _workout(start: str, title: str, sets: list[dict]) -> dict:
    return {
        "start_time": start,
        "end_time": start,
        "exercises": [{"title": title, "sets": sets}],
    }


@pytest.mark.asyncio
async def test_workout_backfill_creates_sessions_and_converts_weights(test_db):
    user = User(device_id="bf-w-0001")
    bench = Exercise(name="Backfill Bench", mechanics="Compound")
    test_db.add_all([user, bench])
    await test_db.flush()

    workouts = [
        _workout("2026-01-05T09:00:00Z", "Bench Press (Barbell)",
                 [{"weight_kg": 40.8233, "reps": 10}, {"weight_kg": 40.8233, "reps": 8}]),
    ]
    sessions, sets, unmapped = await backfill_workouts(
        test_db, user, workouts, {"Bench Press (Barbell)": bench.id}
    )
    assert (sessions, sets, unmapped) == (1, 2, 0)

    rows = (await test_db.execute(select(WorkoutSet))).scalars().all()
    assert {r.weight for r in rows} == {90.0}
    assert {r.reps for r in rows} == {10, 8}


@pytest.mark.asyncio
async def test_workout_backfill_is_idempotent_on_start_time(test_db):
    """Re-running must not double the user's training history."""
    user = User(device_id="bf-w-0002")
    bench = Exercise(name="Backfill Bench", mechanics="Compound")
    test_db.add_all([user, bench])
    await test_db.flush()
    workouts = [
        _workout("2026-01-05T09:00:00Z", "Bench", [{"weight_kg": 40.8233, "reps": 10}])
    ]
    mapping = {"Bench": bench.id}

    await backfill_workouts(test_db, user, workouts, mapping)
    sessions, sets, _ = await backfill_workouts(test_db, user, workouts, mapping)
    assert (sessions, sets) == (0, 0)
    assert len((await test_db.execute(select(WorkoutSession))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_unmapped_titles_are_counted_not_guessed(test_db):
    """The mapping was reviewed by hand; the unreviewed tail must not be invented."""
    user = User(device_id="bf-w-0003")
    bench = Exercise(name="Backfill Bench", mechanics="Compound")
    test_db.add_all([user, bench])
    await test_db.flush()

    workouts = [{
        "start_time": "2026-01-05T09:00:00Z",
        "end_time": "2026-01-05T10:00:00Z",
        "exercises": [
            {"title": "Bench", "sets": [{"weight_kg": 40.8233, "reps": 10}]},
            {"title": "Something Unreviewed", "sets": [{"weight_kg": 20.0, "reps": 5}]},
        ],
    }]
    sessions, sets, unmapped = await backfill_workouts(
        test_db, user, workouts, {"Bench": bench.id}
    )
    assert (sessions, sets, unmapped) == (1, 1, 1)


@pytest.mark.asyncio
async def test_a_workout_with_nothing_resolvable_creates_no_session(test_db):
    user = User(device_id="bf-w-0004")
    test_db.add(user)
    await test_db.flush()

    workouts = [_workout("2026-01-05T09:00:00Z", "Unknown", [{"weight_kg": 20.0, "reps": 5}])]
    sessions, sets, unmapped = await backfill_workouts(test_db, user, workouts, {})
    assert (sessions, sets, unmapped) == (0, 0, 1)
    assert (await test_db.execute(select(WorkoutSession))).scalars().all() == []


@pytest.mark.asyncio
async def test_backfilled_history_feeds_last_performed(test_db):
    """The point of the exercise: rotation needs a date to sort by."""
    from app.services.history_service import last_performed_map

    user = User(device_id="bf-w-0005")
    bench = Exercise(name="Backfill Bench", mechanics="Compound")
    test_db.add_all([user, bench])
    await test_db.flush()

    await backfill_workouts(
        test_db, user,
        [_workout("2026-01-05T09:00:00Z", "Bench", [{"weight_kg": 40.8233, "reps": 10}])],
        {"Bench": bench.id},
    )

    last = await last_performed_map(test_db, user.id, [bench.id])
    assert last[bench.id] == datetime(2026, 1, 5, 9, 0)
