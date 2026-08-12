"""Tests for the suggestion engine"""
import pytest
from datetime import datetime

from sqlalchemy import insert, select

from app.models import (
    User, Exercise, Equipment, EquipmentProfile, MuscleGroup, MovementPattern,
    ExercisePatternMap, StapleExercise, ExercisePreference, DayPlan, PatternGoal,
    TrainingSession, SupersetRound, RoundEntry, EntrySet, SessionState,
    InjuryType, MovementRestriction, UserInjury,
)
from app.models.exercise import exercise_muscle_groups, DifficultyLevel
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

    # difficulty is set because the real catalogue rates 98% of its rows, and
    # novelty suggestions deliberately skip unrated exercises.
    row = Exercise(name="Seated Cable Row", movement_pattern_1="Horizontal Pull",
                   mechanics="Compound", primary_equipment_id=cable.id,
                   difficulty=DifficultyLevel.NOVICE)
    bench = Exercise(name="Dumbbell Bench Press", movement_pattern_1="Horizontal Push",
                     mechanics="Compound", primary_equipment_id=db_bell.id,
                     difficulty=DifficultyLevel.NOVICE)
    pushup = Exercise(name="Push Up", movement_pattern_1="Horizontal Push",
                      mechanics="Compound", primary_equipment_id=None,  # bodyweight
                      difficulty=DifficultyLevel.BEGINNER)
    bb_bench = Exercise(name="Barbell Bench Press", movement_pattern_1="Horizontal Push",
                        mechanics="Compound", primary_equipment_id=cable.id,
                        difficulty=DifficultyLevel.NOVICE)
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
    assert "Dumbbell Bench Press" not in names  # the anchor's opposite
    assert "Seated Cable Row" not in names  # the anchor's own pattern

    # A neutral anchor is never offered as its own partner: core is in the
    # neutral target list, so Plank would otherwise pair with itself.
    self_paired = await partner_suggestions(test_db, user.id, session.id,
                                            anchor_exercise_id=plank.id, position=3)
    assert "Plank" not in [c["exercise_name"] for c in self_paired["candidates"]]
    assert (self_paired["novelty"] or {}).get("exercise_name") != "Plank"


@pytest.mark.asyncio
async def test_novelty_candidate_is_non_staple_compound(test_db):
    user, session, d = await _setup(test_db)
    incline = Exercise(difficulty=DifficultyLevel.NOVICE,
                       name="Incline Dumbbell Bench Press", movement_pattern_1="Horizontal Push",
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


async def _log_completed_sets(test_db, user_id, exercise_id, pattern_id, count):
    """Log `count` completed sets on one exercise, dated inside the current week."""
    now = datetime.utcnow()
    done = TrainingSession(user_id=user_id, state=SessionState.COMPLETED,
                           started_at=now, completed_at=now)
    rnd = SupersetRound(order=1)
    entry = RoundEntry(position=1, exercise_id=exercise_id, pattern_id=pattern_id)
    for n in range(1, count + 1):
        entry.sets.append(EntrySet(set_number=n, weight=60.0, reps=10))
    rnd.entries.append(entry)
    done.rounds.append(rnd)
    test_db.add(done)
    return done


async def _link_muscle_group(test_db, exercise_id, muscle_group_id):
    await test_db.execute(insert(exercise_muscle_groups).values(
        exercise_id=exercise_id, muscle_group_id=muscle_group_id, role="target"))


@pytest.mark.asyncio
async def test_equipment_profile_filters_candidates_but_never_bodyweight(test_db):
    """Bodyweight is always available; equipment not in the profile is not."""
    user, session, d = await _setup(test_db)
    cable_id = d["row"].primary_equipment_id
    test_db.add(EquipmentProfile(user_id=user.id, name="Hotel Gym",
                                 equipment_ids=[cable_id], is_default=True))
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    names = [c["exercise_name"] for c in result["candidates"]]
    # Push Up has primary_equipment_id IS NULL - never filtered on equipment
    assert "Push Up" in names
    # Dumbbell Bench Press needs a dumbbell, which the profile does not have
    assert "Dumbbell Bench Press" not in names
    why = {n["exercise_name"]: n["reason"] for n in result["not_recommended"]}
    assert "Equipment not in your current profile" == why["Dumbbell Bench Press"]


@pytest.mark.asyncio
async def test_equipment_profile_never_filters_the_bodyweight_equipment_row(test_db):
    """Bodyweight is a real equipment row, not a NULL, and must survive a profile.

    Regression guard: the predicate tested for `primary_equipment_id IS NULL`,
    which no catalogue row satisfies - all 209 bodyweight exercises point at
    the "Bodyweight" equipment row. So the always-available rule never fired,
    and the first equipment profile the user created would have hidden every
    push-up, plank and squat jump.
    """
    user, session, d = await _setup(test_db)
    cable_id = d["row"].primary_equipment_id

    bodyweight = Equipment(name="Bodyweight")
    test_db.add(bodyweight)
    await test_db.flush()
    dip = Exercise(name="Bodyweight Dip", movement_pattern_1="Horizontal Push",
                   mechanics="Compound", primary_equipment_id=bodyweight.id,
                   difficulty=DifficultyLevel.BEGINNER)
    test_db.add(dip)
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    test_db.add(StapleExercise(user_id=user.id, pattern_id=d["hpush"].id, exercise_id=dip.id))
    # A profile with only a cable - deliberately no Bodyweight row.
    test_db.add(EquipmentProfile(user_id=user.id, name="Hotel Gym",
                                 equipment_ids=[cable_id], is_default=True))
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    names = [c["exercise_name"] for c in result["candidates"]]
    assert "Bodyweight Dip" in names
    card = next(c for c in result["candidates"] if c["exercise_name"] == "Bodyweight Dip")
    assert card["is_bodyweight"] is True


@pytest.mark.asyncio
async def test_injury_restriction_excludes_with_disclaimer(test_db):
    """Conservative exclusion, disclaimer attached, and severity gating honored."""
    user, session, d = await _setup(test_db)
    injury = InjuryType(name="Rotator Cuff Injury", body_area="Shoulder")
    # Applies at moderate: the user's severity
    injury.restrictions.append(MovementRestriction(
        restriction_type="movement_pattern", restriction_value="Horizontal Push",
        severity_threshold="mild"))
    # Does NOT apply: threshold is above the user's severity
    injury.restrictions.append(MovementRestriction(
        restriction_type="movement_pattern", restriction_value="Horizontal Pull",
        severity_threshold="severe"))
    test_db.add(injury)
    await test_db.flush()
    test_db.add(UserInjury(user_id=user.id, injury_type_id=injury.id,
                           severity="moderate", is_active=True))
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    assert result["candidates"] == []  # every horizontal_push staple is restricted
    assert result["novelty"] is None
    why = {n["exercise_name"]: n["reason"] for n in result["not_recommended"]}
    assert "not medical advice" in why["Dumbbell Bench Press"]
    assert "Rotator Cuff Injury" in why["Dumbbell Bench Press"]
    # Bodyweight gets no injury exemption
    assert "not medical advice" in why["Push Up"]

    # The severe-threshold restriction must NOT fire at moderate severity, so
    # the horizontal_pull staple is still offered as an anchor.
    anchors = await anchor_suggestions(test_db, user.id, session.id)
    pull = next(g for g in anchors["groups"] if g["pattern"]["slug"] == "horizontal_pull")
    assert [c["exercise_name"] for c in pull["staples"]] == ["Seated Cable Row"]


@pytest.mark.asyncio
async def test_weekly_volume_over_limit_excludes_candidates(test_db):
    """Past WEEKLY_SET_LIMIT sets on a muscle group this week -> exercises drop out."""
    user, session, d = await _setup(test_db)
    chest = MuscleGroup(name="Chest", level=1)
    test_db.add(chest)
    await test_db.flush()
    await _link_muscle_group(test_db, d["bench"].id, chest.id)
    await _link_muscle_group(test_db, d["pushup"].id, chest.id)
    # 21 completed sets this week > the 20-set limit
    await _log_completed_sets(test_db, user.id, d["bench"].id, d["hpush"].id, 21)
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    assert result["candidates"] == []
    why = {n["exercise_name"]: n["reason"] for n in result["not_recommended"]}
    assert why["Dumbbell Bench Press"] == "Weekly volume exceeded for Chest (>20 sets)"
    # Bodyweight gets no volume exemption either
    assert why["Push Up"] == "Weekly volume exceeded for Chest (>20 sets)"


@pytest.mark.asyncio
async def test_novelty_pick_is_valid_and_deterministic_within_a_run(test_db):
    """With several eligible candidates the pick is a real one, and stable.

    Asserted on properties rather than a name: the rotation ordering shifts
    across weeks by design, so pinning a specific exercise would be flaky.
    """
    user, session, d = await _setup(test_db)
    candidates = [
        Exercise(name=f"Machine Chest Press {i}", movement_pattern_1="Horizontal Push",
                 mechanics="Compound", primary_equipment_id=None,
                 difficulty=DifficultyLevel.NOVICE)
        for i in range(6)
    ]
    # An isolation movement and a wrong-pattern movement must never be picked
    curl = Exercise(name="Cable Curl", movement_pattern_1="Horizontal Push",
                    mechanics="Isolation", primary_equipment_id=None)
    test_db.add_all(candidates + [curl])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    await test_db.commit()

    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=d["row"].id, position=2)
    novelty = result["novelty"]
    assert novelty is not None
    assert novelty["exercise_name"] in {e.name for e in candidates}
    assert novelty["pattern_slug"] == "horizontal_push"
    assert novelty["is_staple"] is False
    assert novelty["exercise_name"] != "Cable Curl"  # isolation, not a compound
    # Staples and the blacklisted exercise are excluded in SQL now
    assert novelty["exercise_name"] not in {
        "Dumbbell Bench Press", "Push Up", "Barbell Bench Press"}

    again = await partner_suggestions(test_db, user.id, session.id,
                                      anchor_exercise_id=d["row"].id, position=2)
    assert again["novelty"]["exercise_id"] == novelty["exercise_id"]


@pytest.mark.asyncio
async def test_novelty_respects_weekly_volume(test_db):
    """A 'try something new' pick is not exempt from the volume limit."""
    user, session, d = await _setup(test_db)
    incline = Exercise(difficulty=DifficultyLevel.NOVICE,
                       name="Incline Dumbbell Bench Press",
                       movement_pattern_1="Horizontal Push",
                       mechanics="Compound", primary_equipment_id=None)
    chest = MuscleGroup(name="Chest", level=1)
    test_db.add_all([incline, chest])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    await _link_muscle_group(test_db, incline.id, chest.id)
    await test_db.commit()

    # Under the limit: the novel exercise is offered
    await _log_completed_sets(test_db, user.id, d["bench"].id, d["hpush"].id, 5)
    await _link_muscle_group(test_db, d["bench"].id, chest.id)
    await test_db.commit()
    under = await partner_suggestions(test_db, user.id, session.id,
                                      anchor_exercise_id=d["row"].id, position=2)
    assert under["novelty"]["exercise_name"] == "Incline Dumbbell Bench Press"

    # Over the limit on the same muscle group: no novelty pick for it
    await _log_completed_sets(test_db, user.id, d["bench"].id, d["hpush"].id, 21)
    await test_db.commit()
    over = await partner_suggestions(test_db, user.id, session.id,
                                     anchor_exercise_id=d["row"].id, position=2)
    assert over["novelty"] is None


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


async def test_novelty_skips_equipment_the_user_has_never_used(test_db):
    """With no equipment profile, fall back to what the staples demonstrably use.

    The catalogue is full of unconventional implements (Clubbell, Macebell,
    Bulgarian Bag). Suggesting one to somebody who owns none of them is noise
    in the gym, and 'no profile' should not mean 'anything goes'.
    """
    user, session, _d = await _setup(test_db)
    macebell = Equipment(name="Macebell")
    test_db.add(macebell)
    await test_db.flush()
    db_bell = (
        await test_db.execute(select(Equipment).where(Equipment.name == "Dumbbell"))
    ).scalar_one()
    exotic = Exercise(
        name="Macebell 360 Swing", movement_pattern_1="Horizontal Push",
        mechanics="Compound", primary_equipment_id=macebell.id,
        difficulty=DifficultyLevel.INTERMEDIATE,
    )
    # A reachable alternative, so the assertion below proves the macebell was
    # filtered out rather than that nothing was eligible.
    reachable = Exercise(
        name="Dumbbell Floor Press", movement_pattern_1="Horizontal Push",
        mechanics="Compound", primary_equipment_id=db_bell.id,
        difficulty=DifficultyLevel.NOVICE,
    )
    test_db.add_all([exotic, reachable])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    await test_db.commit()
    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=_d["row"].id, position=2)

    # Not a vacuous pass: something is still suggested, just not the macebell.
    assert result["novelty"] is not None
    assert result["novelty"]["exercise_name"] != "Macebell 360 Swing"


async def test_novelty_skips_unrated_and_elite_exercises(test_db):
    """Unknown difficulty is unvetted, and Expert moves are not 'try something new'.

    A two-finger planche push-up has NULL difficulty in the real catalogue, so
    excluding only Advanced/Expert would let it through.
    """
    user, session, _d = await _setup(test_db)
    db_bell = (
        await test_db.execute(select(Equipment).where(Equipment.name == "Dumbbell"))
    ).scalar_one()
    for name, level in [("Planche Push Up", None), ("One Arm Push Up", DifficultyLevel.EXPERT),
                        ("Dumbbell Floor Press", DifficultyLevel.NOVICE)]:
        test_db.add(Exercise(
            name=name, movement_pattern_1="Horizontal Push", mechanics="Compound",
            primary_equipment_id=db_bell.id, difficulty=level,
        ))
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)

    await test_db.commit()
    result = await partner_suggestions(test_db, user.id, session.id,
                                       anchor_exercise_id=_d["row"].id, position=2)

    # Not a vacuous pass: a rated candidate is still offered.
    assert result["novelty"] is not None
    assert result["novelty"]["exercise_name"] not in {"Planche Push Up", "One Arm Push Up"}
