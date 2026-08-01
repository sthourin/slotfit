"""Tests for progression math"""
import pytest
from datetime import datetime

from sqlalchemy import select

from app.models import (
    User, Exercise, MovementPattern, StapleExercise,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.services.pattern_taxonomy import seed_movement_patterns
from app.services.progression_service import estimate_1rm, next_target, pattern_trend


def test_estimate_1rm_epley():
    assert estimate_1rm(100.0, 10) == pytest.approx(133.33, abs=0.01)
    assert estimate_1rm(100.0, 1) == pytest.approx(103.33, abs=0.01)


def test_next_target_adds_rep_below_range_top():
    # Last: 3x10 @ 120, range 8-12 -> same weight, 11 reps
    target = next_target([(120.0, 10), (120.0, 10), (120.0, 10)])
    assert target == {"weight": 120.0, "reps": 11, "sets": 3, "last_summary": "3x10 @ 120"}


def test_next_target_bumps_weight_at_range_top():
    # All sets at rep_max -> +increment, back to rep_min
    target = next_target([(120.0, 12), (120.0, 12), (120.0, 12)], increment=5.0)
    assert target == {"weight": 125.0, "reps": 8, "sets": 3, "last_summary": "3x12 @ 120"}


def test_next_target_no_history():
    target = next_target([])
    assert target == {"weight": None, "reps": 8, "sets": 3, "last_summary": None}


def test_next_target_bodyweight_sets():
    # Weight None (bodyweight): progress reps only
    target = next_target([(None, 10), (None, 10)])
    assert target["weight"] is None
    assert target["reps"] == 11
    assert target["sets"] == 2


async def _completed_session(test_db, user, ex, pattern, when, weight, reps):
    s = TrainingSession(user_id=user.id, state=SessionState.COMPLETED, started_at=when, completed_at=when)
    r = SupersetRound(order=1)
    e = RoundEntry(position=1, exercise_id=ex.id, pattern_id=pattern.id)
    e.sets.append(EntrySet(set_number=1, weight=weight, reps=reps))
    r.entries.append(e)
    s.rounds.append(r)
    test_db.add(s)
    await test_db.commit()


@pytest.mark.asyncio
async def test_pattern_trend_normalizes_across_staples(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, row])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    test_db.add(StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id))
    await test_db.commit()

    # Week 1: 100x10 (e1RM 133.3, baseline -> index 1.0); Week 3: 110x10 (index 1.1)
    await _completed_session(test_db, user, row, hp, datetime(2026, 1, 5, 9), 100.0, 10)
    await _completed_session(test_db, user, row, hp, datetime(2026, 1, 19, 9), 110.0, 10)

    trend = await pattern_trend(test_db, user.id, hp.id, weeks=52)
    assert len(trend) == 2
    assert trend[0]["index"] == pytest.approx(1.0)
    assert trend[1]["index"] == pytest.approx(1.1, abs=0.001)
    assert trend[0]["week_start"] < trend[1]["week_start"]
