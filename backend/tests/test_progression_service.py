"""Tests for progression math"""
import pytest
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.models import (
    User, Exercise, Equipment, MovementPattern, StapleExercise,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
    BodyweightReading,
)
from app.models.exercise import SetProtocol
from app.services.pattern_taxonomy import seed_movement_patterns
from app.services.progression_service import (
    estimate_1rm, next_target, compute_entry_target, pattern_trend,
)


def _monday_weeks_ago(weeks_back: int) -> date:
    """Monday of the week `weeks_back` weeks before the current week.

    Anchoring fixture dates to date.today() (rather than a hardcoded
    calendar date) keeps these tests true no matter when they run, since
    pattern_trend's window filtering is itself date.today()-relative.
    """
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    return this_monday - timedelta(weeks=weeks_back)


def _dt(d: date, hour: int = 9) -> datetime:
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=hour)


def test_estimate_1rm_epley():
    assert estimate_1rm(100.0, 10) == pytest.approx(133.33, abs=0.01)
    assert estimate_1rm(100.0, 1) == pytest.approx(103.33, abs=0.01)


def test_next_target_adds_rep_below_range_top():
    # Last: 3x10 @ 120, range 8-12 -> same weight, 11 reps
    target = next_target([(120.0, 10), (120.0, 10), (120.0, 10)])
    assert target == {
        "weight": 120.0, "reps": 11, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": "3x10 @ 120",
    }


def test_next_target_bumps_weight_at_range_top():
    # All sets at rep_max -> +increment, back to rep_min
    target = next_target([(120.0, 12), (120.0, 12), (120.0, 12)], increment=5.0)
    assert target == {
        "weight": 125.0, "reps": 8, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": "3x12 @ 120",
    }


def test_next_target_no_history():
    target = next_target([])
    assert target == {
        "weight": None, "reps": 8, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": None,
    }


def test_next_target_bodyweight_never_regresses_past_rep_max():
    """Bodyweight has no load to add, so reps must keep climbing past rep_max.

    Regression guard: this returned 12 after a logged 15, i.e. prescribed less
    work than was just performed, and would have done so forever.
    """
    target = next_target([(None, 15), (None, 15)], rep_max=12)
    assert target["reps"] == 16
    assert target["reps_goal"] == "target"
    assert target["weight"] is None
    assert target["sets"] == 2
    assert target["last_summary"] == "2x15"


def test_next_target_bodyweight_below_rep_max_still_adds_one():
    target = next_target([(None, 9), (None, 9)], rep_max=12)
    assert target["reps"] == 10


def test_next_target_amrap_beats_last_count_without_touching_load():
    """AMRAP always clears a 12-rep ceiling, so rep-range logic must not drive load.

    Regression guard: this returned weight 40 from a logged 35, and escalated
    by the increment every session indefinitely.
    """
    target = next_target(
        [(35.0, 22), (35.0, 22)], rep_max=12, protocol=SetProtocol.AMRAP
    )
    assert target["weight"] == 35.0
    assert target["reps"] == 22
    assert target["reps_goal"] == "beat"
    assert target["last_summary"] == "2x22 @ 35"


def test_next_target_amrap_uses_best_set_as_the_bar():
    """The number to beat is the best set performed, not the worst."""
    target = next_target([(35.0, 22), (35.0, 18)], protocol=SetProtocol.AMRAP)
    assert target["reps"] == 22
    assert target["reps_goal"] == "beat"


def test_next_target_time_only_prescribes_nothing():
    """A rower logged in seconds gets no rep target and no invented load.

    Regression guard: this returned reps 9 and a summary of '0@bw, 0@bw'.
    """
    target = next_target(
        [(None, None, 300), (None, None, 240)], protocol=SetProtocol.TIME
    )
    assert target["reps"] is None
    assert target["reps_goal"] is None
    assert target["weight"] is None
    assert target["time_seconds"] is None
    assert target["last_summary"] == "300s, 240s"


def test_next_target_time_only_uniform_durations_summarise_compactly():
    target = next_target(
        [(None, None, 300), (None, None, 300)], protocol=SetProtocol.TIME
    )
    assert target["last_summary"] == "2x300s"


def test_next_target_emom_behaves_like_reps():
    """EMOM reps are prescribed, so double progression still applies."""
    target = next_target(
        [(50.0, 12), (50.0, 12)], rep_max=12, increment=5.0, protocol=SetProtocol.EMOM
    )
    assert target["weight"] == 55.0
    assert target["reps"] == 8
    assert target["reps_goal"] == "target"


def test_next_target_bodyweight_sets():
    # Weight None (bodyweight): progress reps only
    target = next_target([(None, 10), (None, 10)])
    assert target["weight"] is None
    assert target["reps"] == 11
    assert target["sets"] == 2


async def _cable_id(test_db) -> int:
    """Id of a Cable Machine equipment row, created on demand.

    Loaded-lift fixtures must carry real equipment. Every row in the real
    catalogue has some; NULL means bodyweight, and bodyweight work with no
    weigh-in is deliberately unscoreable for e1RM - so an equipment-less
    "Cable Row" would silently exercise the bodyweight path instead.
    """
    result = await test_db.execute(select(Equipment).where(Equipment.name == "Cable Machine"))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing.id
    equipment = Equipment(name="Cable Machine")
    test_db.add(equipment)
    await test_db.flush()
    return equipment.id


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
    test_db.add(user)
    cable_id = await _cable_id(test_db)
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound",
                   primary_equipment_id=cable_id)
    test_db.add(row)
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    test_db.add(StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id))
    await test_db.commit()

    # Older week: 100x10 (e1RM 133.3, baseline -> index 1.0).
    # Newer week: 110x10 (index 1.1).
    when_older = _dt(_monday_weeks_ago(4))
    when_newer = _dt(_monday_weeks_ago(2))

    await _completed_session(test_db, user, row, hp, when_older, 100.0, 10)
    await _completed_session(test_db, user, row, hp, when_newer, 110.0, 10)

    trend = await pattern_trend(test_db, user.id, hp.id, weeks=52)
    assert len(trend) == 2
    assert trend[0]["index"] == pytest.approx(1.0)
    assert trend[1]["index"] == pytest.approx(1.1, abs=0.001)
    assert trend[0]["week_start"] < trend[1]["week_start"]


@pytest.mark.asyncio
async def test_pattern_trend_includes_bodyweight_staples_via_leverage(test_db):
    """A push-up-only pattern must produce a trend once bodyweight is known.

    Before leverage every set had weight=None and was skipped outright, so the
    series came back empty no matter how much work was logged.
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="trend-bw-0001")
    bodyweight_equipment = Equipment(name="Bodyweight")
    test_db.add_all([user, bodyweight_equipment])
    await test_db.flush()
    push_up = Exercise(
        name="Trend Push Up", movement_pattern_1="Horizontal Push", mechanics="Compound",
        primary_equipment_id=bodyweight_equipment.id, bodyweight_fraction=0.64,
    )
    test_db.add(push_up)
    await test_db.flush()
    result = await test_db.execute(
        select(MovementPattern).where(MovementPattern.slug == "horizontal_push")
    )
    hpush = result.scalar_one()
    test_db.add(StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=push_up.id))
    test_db.add(BodyweightReading(
        user_id=user.id, weight=200.0,
        recorded_at=_dt(_monday_weeks_ago(6)), source="manual",
    ))
    await test_db.commit()

    # Same bodyweight, more reps: 10 then 20.
    await _completed_session(test_db, user, push_up, hpush, _dt(_monday_weeks_ago(4)), None, 10)
    await _completed_session(test_db, user, push_up, hpush, _dt(_monday_weeks_ago(2)), None, 20)

    trend = await pattern_trend(test_db, user.id, hpush.id, weeks=52)
    assert len(trend) == 2
    assert trend[0]["index"] == pytest.approx(1.0)
    assert trend[1]["index"] > 1.0


@pytest.mark.asyncio
async def test_pattern_trend_skips_bodyweight_work_with_no_readings(test_db):
    """With no weigh-in there is no honest number, so it is left out."""
    await seed_movement_patterns(test_db)
    user = User(device_id="trend-nobw-0001")
    bodyweight_equipment = Equipment(name="Bodyweight")
    test_db.add_all([user, bodyweight_equipment])
    await test_db.flush()
    push_up = Exercise(
        name="Trend Push Up", movement_pattern_1="Horizontal Push", mechanics="Compound",
        primary_equipment_id=bodyweight_equipment.id, bodyweight_fraction=0.64,
    )
    test_db.add(push_up)
    await test_db.flush()
    result = await test_db.execute(
        select(MovementPattern).where(MovementPattern.slug == "horizontal_push")
    )
    hpush = result.scalar_one()
    test_db.add(StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=push_up.id))
    await test_db.commit()

    await _completed_session(test_db, user, push_up, hpush, _dt(_monday_weeks_ago(4)), None, 10)

    assert await pattern_trend(test_db, user.id, hpush.id, weeks=52) == []


@pytest.mark.asyncio
async def test_compute_entry_target_with_history(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, row])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    await test_db.commit()

    s = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                        started_at=_dt(_monday_weeks_ago(1)), completed_at=_dt(_monday_weeks_ago(1)))
    r = SupersetRound(order=1)
    e = RoundEntry(position=1, exercise_id=row.id, pattern_id=hp.id)
    e.sets.append(EntrySet(set_number=1, weight=120.0, reps=10))
    e.sets.append(EntrySet(set_number=2, weight=120.0, reps=10))
    e.sets.append(EntrySet(set_number=3, weight=120.0, reps=10))
    r.entries.append(e)
    s.rounds.append(r)
    test_db.add(s)
    await test_db.commit()

    target = await compute_entry_target(test_db, user.id, row.id)
    assert target == {
        "weight": 120.0, "reps": 11, "sets": 3, "time_seconds": None,
        "reps_goal": "target", "last_summary": "3x10 @ 120",
    }


@pytest.mark.asyncio
async def test_compute_entry_target_no_history(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([user, row])
    await test_db.commit()

    target = await compute_entry_target(test_db, user.id, row.id)
    assert target is None


@pytest.mark.asyncio
async def test_pattern_trend_averages_across_multiple_staples(test_db):
    """The whole point of pattern_trend is averaging per-staple indices, each
    normalized to its OWN baseline. A single-staple fixture can't distinguish
    correct averaging from a broken implementation - this uses two staples
    progressing at different rates (+10% and +20%) so the expected weekly
    index (~1.15) is only reachable by actually averaging both.
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    test_db.add(user)
    cable_id = await _cable_id(test_db)
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound",
                   primary_equipment_id=cable_id)
    csr = Exercise(name="Chest-Supported Row", movement_pattern_1="Horizontal Pull", mechanics="Compound",
                   primary_equipment_id=cable_id)
    test_db.add_all([row, csr])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    test_db.add_all([
        StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id),
        StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=csr.id),
    ])
    await test_db.commit()

    when_older = _dt(_monday_weeks_ago(4))
    when_newer = _dt(_monday_weeks_ago(2))

    # Cable Row: 100 -> 110 (+10%, index 1.10)
    await _completed_session(test_db, user, row, hp, when_older, 100.0, 10)
    await _completed_session(test_db, user, row, hp, when_newer, 110.0, 10)
    # Chest-Supported Row: 100 -> 120 (+20%, index 1.20)
    await _completed_session(test_db, user, csr, hp, when_older, 100.0, 10)
    await _completed_session(test_db, user, csr, hp, when_newer, 120.0, 10)

    trend = await pattern_trend(test_db, user.id, hp.id, weeks=52)
    assert len(trend) == 2
    assert trend[0]["index"] == pytest.approx(1.0)
    # Average of 1.10 and 1.20, not either rate alone.
    assert trend[1]["index"] == pytest.approx(1.15, abs=0.001)


@pytest.mark.asyncio
async def test_pattern_trend_excludes_staple_with_no_usable_weights(test_db):
    """A staple whose every set has weight=None (e.g. a bodyweight staple)
    contributes no e1RM values at all. It must be silently excluded from the
    per-week average rather than crashing it (e.g. ZeroDivisionError/KeyError).
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    test_db.add(user)
    cable_id = await _cable_id(test_db)
    row = Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound",
                   primary_equipment_id=cable_id)
    # Deliberately no equipment: this is the bodyweight staple the test excludes.
    inverted_row = Exercise(name="Inverted Row", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add_all([row, inverted_row])
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    test_db.add_all([
        StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id),
        StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=inverted_row.id),
    ])
    await test_db.commit()

    when_older = _dt(_monday_weeks_ago(4))
    when_newer = _dt(_monday_weeks_ago(2))

    await _completed_session(test_db, user, row, hp, when_older, 100.0, 10)
    await _completed_session(test_db, user, row, hp, when_newer, 110.0, 10)
    # Bodyweight staple: weight always None -> no usable e1RM.
    await _completed_session(test_db, user, inverted_row, hp, when_older, None, 10)
    await _completed_session(test_db, user, inverted_row, hp, when_newer, None, 12)

    trend = await pattern_trend(test_db, user.id, hp.id, weeks=52)
    assert len(trend) == 2
    # Degenerates to the single usable staple (Cable Row) - no crash.
    assert trend[0]["index"] == pytest.approx(1.0)
    assert trend[1]["index"] == pytest.approx(1.1, abs=0.001)


@pytest.mark.asyncio
async def test_pattern_trend_baseline_survives_high_frequency_staple(test_db):
    """Regression for a real bug: pattern_trend used to cap each staple's
    fetched history at `limit_sessions=weeks * 3` with no date filter at all.
    A staple logged more often than ~3x/week (e.g. a warm-up movement done
    nearly every session) could have its true earliest in-window session
    evicted by that count cap, silently promoting a later session to be the
    baseline. Fetching by `since=<cutoff>` instead of guessing a count fixes
    this.

    Fixture: 5 sessions/week for 3 weeks (15 total) against
    pattern_trend(weeks=3) - i.e. 15 sessions vs. the old cap of
    weeks*3 == 9. Under the old count-based approach, the newest 9 of these
    15 sessions are the 5 from week_newer plus 4 of week_mid's 5, so
    week_older's entire 5 sessions - despite being inside the 3-week window -
    are dropped outright: len(trend) would be 2, not 3, and trend[0] would
    be week_mid (wrongly used as baseline) instead of week_older.
    """
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    test_db.add(user)
    cable_id = await _cable_id(test_db)
    rower = Exercise(name="Rower Warm-Up", movement_pattern_1="Horizontal Pull", mechanics="Compound",
                     primary_equipment_id=cable_id)
    test_db.add(rower)
    await test_db.flush()
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()
    test_db.add(StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=rower.id))
    await test_db.commit()

    week_older = _monday_weeks_ago(3)
    week_mid = _monday_weeks_ago(2)
    week_newer = _monday_weeks_ago(1)

    for week_start, base_weight in ((week_older, 100.0), (week_mid, 110.0), (week_newer, 120.0)):
        for day_offset in range(5):
            when = datetime.combine(week_start, datetime.min.time()) + timedelta(days=day_offset, hours=9)
            await _completed_session(test_db, user, rower, hp, when, base_weight + day_offset, 10)

    trend = await pattern_trend(test_db, user.id, hp.id, weeks=3)

    assert len(trend) == 3
    assert trend[0]["week_start"] == week_older
    assert trend[0]["index"] == pytest.approx(1.0)
