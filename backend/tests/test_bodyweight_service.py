"""Tests for bodyweight resolution and effective load."""
from datetime import datetime

import pytest

from app.models import BodyweightReading, Exercise, User
from app.services.bodyweight_service import (
    bodyweight_at,
    bodyweight_timeline,
    effective_load,
    resolve_bodyweight,
)

BODYWEIGHT_ID = 2

TIMELINE = [
    (datetime(2026, 1, 1), 200.0),
    (datetime(2026, 6, 1), 190.0),
]


def _bw(name: str, fraction: float | None) -> Exercise:
    return Exercise(
        name=name, primary_equipment_id=BODYWEIGHT_ID, bodyweight_fraction=fraction
    )


def test_resolve_uses_the_reading_in_effect_on_the_day():
    assert resolve_bodyweight(TIMELINE, datetime(2026, 3, 1)) == 200.0
    assert resolve_bodyweight(TIMELINE, datetime(2026, 7, 1)) == 190.0


def test_resolve_on_an_exact_reading_date_uses_that_reading():
    assert resolve_bodyweight(TIMELINE, datetime(2026, 6, 1)) == 190.0


def test_resolve_before_any_reading_falls_back_to_the_earliest():
    """Sets predating the first weigh-in still need a number; the nearest is it."""
    assert resolve_bodyweight(TIMELINE, datetime(2025, 12, 1)) == 200.0


def test_resolve_with_no_readings_is_none():
    assert resolve_bodyweight([], datetime(2026, 3, 1)) is None


def test_effective_load_scales_bodyweight_by_the_curated_fraction():
    assert effective_load(_bw("Bodyweight Push Up", 0.64), None, 200.0, BODYWEIGHT_ID) == pytest.approx(128.0)


def test_effective_load_adds_external_load_to_bodyweight():
    """A weighted vest adds to the bodyweight component, it does not replace it."""
    assert effective_load(_bw("Bodyweight Push Up", 0.64), 25.0, 200.0, BODYWEIGHT_ID) == pytest.approx(153.0)


def test_effective_load_uses_the_default_fraction_when_uncurated():
    assert effective_load(_bw("Some Uncurated Move", None), None, 100.0, BODYWEIGHT_ID) == pytest.approx(64.0)


def test_effective_load_falls_back_to_the_curated_table_by_name():
    """A row seeded on another database still resolves from the code table."""
    assert effective_load(_bw("Arm Circles", None), None, 200.0, BODYWEIGHT_ID) == pytest.approx(10.0)


def test_effective_load_of_a_loaded_exercise_is_just_the_logged_weight():
    deadlift = Exercise(name="Trap Bar Deadlift", primary_equipment_id=17)
    assert effective_load(deadlift, 315.0, 200.0, BODYWEIGHT_ID) == 315.0


def test_effective_load_without_a_bodyweight_reading_is_none_for_bodyweight_work():
    """Better to score nothing than to invent a bodyweight."""
    assert effective_load(_bw("Bodyweight Push Up", 0.64), None, None, BODYWEIGHT_ID) is None


def test_effective_load_of_a_loaded_exercise_needs_no_reading():
    deadlift = Exercise(name="Trap Bar Deadlift", primary_equipment_id=17)
    assert effective_load(deadlift, 315.0, None, BODYWEIGHT_ID) == 315.0


@pytest.mark.asyncio
async def test_bodyweight_at_reads_the_latest_prior_reading(test_db):
    user = User(device_id="bw-at-0001")
    test_db.add(user)
    await test_db.flush()
    test_db.add_all([
        BodyweightReading(user_id=user.id, weight=200.0, recorded_at=datetime(2026, 1, 1), source="manual"),
        BodyweightReading(user_id=user.id, weight=190.0, recorded_at=datetime(2026, 6, 1), source="manual"),
    ])
    await test_db.flush()

    assert await bodyweight_at(test_db, user.id, datetime(2026, 3, 1)) == 200.0
    assert await bodyweight_at(test_db, user.id, datetime(2026, 7, 1)) == 190.0


@pytest.mark.asyncio
async def test_bodyweight_timeline_is_ascending(test_db):
    user = User(device_id="bw-timeline-0001")
    test_db.add(user)
    await test_db.flush()
    test_db.add_all([
        BodyweightReading(user_id=user.id, weight=190.0, recorded_at=datetime(2026, 6, 1), source="manual"),
        BodyweightReading(user_id=user.id, weight=200.0, recorded_at=datetime(2026, 1, 1), source="manual"),
    ])
    await test_db.flush()

    timeline = await bodyweight_timeline(test_db, user.id)
    assert [w for _dt, w in timeline] == [200.0, 190.0]


@pytest.mark.asyncio
async def test_timeline_is_scoped_to_one_user(test_db):
    mine = User(device_id="bw-mine-0001")
    theirs = User(device_id="bw-theirs-0001")
    test_db.add_all([mine, theirs])
    await test_db.flush()
    test_db.add_all([
        BodyweightReading(user_id=mine.id, weight=200.0, recorded_at=datetime(2026, 1, 1), source="manual"),
        BodyweightReading(user_id=theirs.id, weight=150.0, recorded_at=datetime(2026, 1, 1), source="manual"),
    ])
    await test_db.flush()

    assert [w for _dt, w in await bodyweight_timeline(test_db, mine.id)] == [200.0]
