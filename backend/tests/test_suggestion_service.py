"""Tests for the suggestion engine"""
import pytest
from datetime import datetime

from sqlalchemy import insert, select

from app.models import (
    User, Exercise, Equipment, MuscleGroup, MovementPattern, ExercisePatternMap,
    StapleExercise, ExercisePreference, DayPlan, PatternGoal,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
)
from app.models.exercise import exercise_muscle_groups
from app.services.pattern_taxonomy import seed_movement_patterns, seed_exercise_pattern_map
from app.services.suggestion_service import (
    anchor_suggestions, partner_suggestions, _diverse_limit,
)


async def _pattern(db, slug):
    result = await db.execute(select(MovementPattern).where(MovementPattern.slug == slug))
    return result.scalar_one()


async def _setup(test_db):
    """User with a day plan (pull+push goals), staples on both patterns, one active session."""
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    cable = Equipment(name="Cable Machine")
    db_bell = Equipment(name="Dumbbell")
    test_db.add_all([user, cable, db_bell])
    await test_db.flush()

    row = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull",
                   mechanics="Compound", primary_equipment_id=cable.id)
    bench = Exercise(name="Dumbbell Bench Press", movement_pattern_1="Horizontal Push",
                     mechanics="Compound", primary_equipment_id=db_bell.id)
    pushup = Exercise(name="Push Up", movement_pattern_1="Horizontal Push",
                      mechanics="Compound", primary_equipment_id=None)  # bodyweight
    bb_bench = Exercise(name="Barbell Bench Press", movement_pattern_1="Horizontal Push",
                        mechanics="Compound", primary_equipment_id=cable.id)
    test_db.add_all([row, bench, pushup, bb_bench])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    hp = await _pattern(test_db, "horizontal_pull")
    hpush = await _pattern(test_db, "horizontal_push")

    test_db.add_all([
        StapleExercise(user_id=user.id, pattern_id=hp.id, exercise_id=row.id),
        StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=bench.id),
        StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=pushup.id),
        # A staple the user later soured on - in the pool, so the blacklist
        # filter has something to reject and explain.
        StapleExercise(user_id=user.id, pattern_id=hpush.id, exercise_id=bb_bench.id),
    ])
    # Blacklist barbell bench
    test_db.add(ExercisePreference(user_id=user.id, exercise_id=bb_bench.id, preference="never"))

    plan = DayPlan(user_id=user.id, name="Full Body A", warmup_preferences=[], rounds_target=3)
    plan.goals.append(PatternGoal(pattern_id=hp.id, required=True, target_sets=3))
    plan.goals.append(PatternGoal(pattern_id=hpush.id, required=True, target_sets=3))
    test_db.add(plan)
    await test_db.flush()

    session = TrainingSession(user_id=user.id, day_plan_id=plan.id,
                              state=SessionState.ACTIVE, started_at=datetime(2026, 7, 29, 9))
    test_db.add(session)
    await test_db.commit()
    return user, session, {"row": row, "bench": bench, "pushup": pushup, "bb_bench": bb_bench,
                           "hp": hp, "hpush": hpush}


@pytest.mark.asyncio
async def test_anchor_groups_uncovered_goals_first(test_db):
    user, session, d = await _setup(test_db)
    result = await anchor_suggestions(test_db, user.id, session.id)

    slugs = [g["pattern"]["slug"] for g in result["groups"]]
    assert "horizontal_pull" in slugs and "horizontal_push" in slugs
    for group in result["groups"]:
        assert group["covered"] is False
        names = [c["exercise_name"] for c in group["staples"]]
        assert "Barbell Bench Press" not in names  # blacklisted


@pytest.mark.asyncio
async def test_anchor_freeform_session_falls_back_to_all_staple_patterns(test_db):
    """No day plan means no coverage to chase - offer every staple pattern."""
    user, session, d = await _setup(test_db)
    plank = Exercise(name="Plank", movement_pattern_1="Isometric Hold",
                     mechanics="Compound", primary_equipment_id=None)
    test_db.add(plank)
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    core = await _pattern(test_db, "core")
    test_db.add(StapleExercise(user_id=user.id, pattern_id=core.id, exercise_id=plank.id))

    free = TrainingSession(user_id=user.id, day_plan_id=None,
                           state=SessionState.ACTIVE, started_at=datetime(2026, 7, 29, 9))
    test_db.add(free)
    await test_db.commit()

    result = await anchor_suggestions(test_db, user.id, free.id)

    slugs = [g["pattern"]["slug"] for g in result["groups"]]
    # Every pattern the user has an active staple for, none of them covered
    assert slugs == ["horizontal_pull", "horizontal_push", "core"]  # display_order
    for group in result["groups"]:
        assert group["covered"] is False
        assert group["staples"]
    names = {c["exercise_name"] for g in result["groups"] for c in g["staples"]}
    assert names == {"Seated Cable Row", "Dumbbell Bench Press", "Push Up", "Plank"}
    # Filters still apply on the fallback path
    assert "Barbell Bench Press" not in names
    assert [n["exercise_name"] for n in result["not_recommended"]] == ["Barbell Bench Press"]


@pytest.mark.asyncio
async def test_anchor_goal_ordering_unchanged_when_a_goal_is_covered(test_db):
    """The goal-driven path is untouched: uncovered goals still sort first."""
    user, session, d = await _setup(test_db)
    # Log 3 completed horizontal_pull sets in THIS session -> that goal is covered
    rnd = SupersetRound(session_id=session.id, order=1)
    entry = RoundEntry(position=1, exercise_id=d["row"].id, pattern_id=d["hp"].id)
    for n in range(1, 4):
        entry.sets.append(EntrySet(set_number=n, weight=100.0, reps=10))
    rnd.entries.append(entry)
    test_db.add(rnd)
    await test_db.commit()

    result = await anchor_suggestions(test_db, user.id, session.id)

    assert [g["pattern"]["slug"] for g in result["groups"]] == [
        "horizontal_push",  # uncovered -> first
        "horizontal_pull",  # covered -> last
    ]
    assert [g["covered"] for g in result["groups"]] == [False, True]


def test_diverse_limit_fills_the_cap_across_uneven_reason_types():
    """Diversity first, then top up - don't return 6 when 10 are available."""
    rejected = [
        {"exercise_name": f"Blacklisted {i}",
         "reason": "Marked never (blacklisted in your preferences)"}
        for i in range(12)
    ]
    rejected.append({
        "exercise_name": "Overhead Press",
        "reason": "May aggravate Rotator Cuff Injury "
                  "(not medical advice - consult a healthcare professional)",
    })

    result = _diverse_limit(rejected)

    assert len(result) == 10  # cap filled, not the 6 the even slice alone gives
    assert len({e["reason"].split("(")[0] for e in result}) == 2  # still diverse
    assert len({e["exercise_name"] for e in result}) == 10  # no duplicates


def test_diverse_limit_never_exceeds_the_cap_or_pads_short_input():
    single_type = [
        {"exercise_name": f"E{i}", "reason": "Equipment not in your current profile"}
        for i in range(25)
    ]
    assert len(_diverse_limit(single_type)) == 10
    assert _diverse_limit([]) == []
    assert len(_diverse_limit(single_type[:3])) == 3


@pytest.mark.asyncio
async def test_partner_suggests_opposite_pattern(test_db):
    user, session, d = await _setup(test_db)
    # Anchor = cable row (horizontal_pull) -> partners must be horizontal_push staples
    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert "Dumbbell Bench Press" in names
    assert "Push Up" in names
    assert "Barbell Bench Press" not in names  # blacklisted
    reasons = [n["reason"] for n in result["not_recommended"]]
    assert any("never" in r.lower() or "blacklist" in r.lower() for r in reasons)
    assert [n["exercise_name"] for n in result["not_recommended"]] == ["Barbell Bench Press"]


@pytest.mark.asyncio
async def test_partner_ranked_least_recent_first(test_db):
    user, session, d = await _setup(test_db)
    # Bench performed recently; push up never -> push up ranks first
    done = TrainingSession(user_id=user.id, state=SessionState.COMPLETED,
                           started_at=datetime(2026, 7, 27, 9), completed_at=datetime(2026, 7, 27, 10))
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=d["bench"].id, pattern_id=d["hpush"].id)
    entry.sets.append(EntrySet(set_number=1, weight=60.0, reps=10))
    rnd.entries.append(entry)
    done.rounds.append(rnd)
    test_db.add(done)
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert names.index("Push Up") < names.index("Dumbbell Bench Press")
    # Bench card carries a progression target from history
    bench_card = next(c for c in result["candidates"] if c["exercise_name"] == "Dumbbell Bench Press")
    assert bench_card["target"]["reps"] == 11


@pytest.mark.asyncio
async def test_position_three_offers_neutral_patterns(test_db):
    user, session, d = await _setup(test_db)
    plank = Exercise(name="Plank", movement_pattern_1="Isometric Hold",
                     mechanics="Compound", primary_equipment_id=None)
    test_db.add(plank)
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    core = await _pattern(test_db, "core")
    test_db.add(StapleExercise(user_id=user.id, pattern_id=core.id, exercise_id=plank.id))
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=3)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert "Plank" in names
    # The antagonist pair is NOT re-offered at position 3
    assert "Dumbbell Bench Press" not in names or "Plank" in names


@pytest.mark.asyncio
async def test_novelty_candidate_is_non_staple_compound(test_db):
    user, session, d = await _setup(test_db)
    incline = Exercise(name="Incline Dumbbell Bench Press", movement_pattern_1="Horizontal Push",
                       mechanics="Compound", primary_equipment_id=None)
    test_db.add(incline)
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    assert result["novelty"] is not None
    assert result["novelty"]["exercise_name"] == "Incline Dumbbell Bench Press"
    assert result["novelty"]["is_staple"] is False


@pytest.mark.asyncio
async def test_weekly_volume_filter_handles_unloaded_exercises(test_db):
    """The weekly-volume filter must eager-load muscle_groups.

    _weekly_sets_by_muscle_group re-queries Exercise rows for whatever was
    logged this week - which includes exercises outside the staple pool that
    were never loaded with their muscle_groups relationship. Accessing a lazy
    many-to-many on an async session raises MissingGreenlet, so the query has
    to load it eagerly.
    """
    user, session, d = await _setup(test_db)
    user_id, session_id = user.id, session.id

    quad = MuscleGroup(name="Quadriceps", level=1)
    leg_press = Exercise(name="Leg Press", movement_pattern_1="Knee Dominant",
                         mechanics="Compound", primary_equipment_id=None)
    test_db.add_all([quad, leg_press])
    await test_db.flush()
    await test_db.execute(insert(exercise_muscle_groups).values(
        exercise_id=leg_press.id, muscle_group_id=quad.id, role="target"))

    # Logged this week, but never a staple -> not in the identity map when
    # the volume filter goes looking for it.
    now = datetime.utcnow()
    logged = TrainingSession(user_id=user_id, state=SessionState.COMPLETED,
                             started_at=now, completed_at=now)
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=leg_press.id, pattern_id=d["hp"].id)
    entry.sets.append(EntrySet(set_number=1, weight=200.0, reps=10))
    rnd.entries.append(entry)
    logged.rounds.append(rnd)
    test_db.add(logged)
    await test_db.commit()
    # Simulate a fresh request: nothing pre-loaded in the identity map.
    test_db.expire_all()

    result = await anchor_suggestions(test_db, user_id, session_id)
    assert len(result["groups"]) == 2
