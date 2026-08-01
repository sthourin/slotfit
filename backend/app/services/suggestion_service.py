"""
Anchor and partner suggestion engine.

Anchors: the user's staples grouped by the session's uncovered pattern goals.
Partners: opposite-pattern staples for position 2, neutral/uncovered patterns
for position 3, ranked least-recently-performed first. All lists pass through
blacklist, injury, equipment, and weekly-volume filters, and rejected
exercises are reported in a "why not" list.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.exercise import Exercise
from app.models.equipment_profile import EquipmentProfile
from app.models.movement_pattern import MovementPattern, ExercisePatternMap
from app.models.staple import StapleExercise, ExercisePreference
from app.models.day_plan import PatternGoal
from app.models.training_session import (
    TrainingSession,
    SupersetRound,
    RoundEntry,
    EntrySet,
)
from app.models.injury import (
    UserInjury,
    InjuryType,
    MovementRestriction,
    injury_movement_restrictions,
)
from app.services.history_service import last_performed_map
from app.services.progression_service import compute_entry_target

WEEKLY_SET_LIMIT = 20
NOVELTY_STALENESS_DAYS = 90
SEVERITY_ORDER = {"mild": 0, "moderate": 1, "severe": 2}

# Novelty scan: how many candidate rows to consider, and the coprime
# multiplier/modulus that shuffle the id space so the scan window is not
# permanently pinned to the lowest ids. Both prime, so id * stride % modulus
# visits every residue.
NOVELTY_SCAN_LIMIT = 200
NOVELTY_ROTATION_STRIDE = 7919
NOVELTY_ROTATION_MODULUS = 9973


async def _blacklisted_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = await db.execute(
        select(ExercisePreference.exercise_id).where(
            ExercisePreference.user_id == user_id,
            ExercisePreference.preference == "never",
        )
    )
    return {row[0] for row in result.all()}


async def _injury_restrictions(db: AsyncSession, user_id: int) -> list[dict]:
    """Active restrictions as [{"type", "value", "injury_name"}], severity-gated."""
    result = await db.execute(
        select(MovementRestriction, UserInjury.severity, InjuryType.name)
        .join(
            injury_movement_restrictions,
            injury_movement_restrictions.c.restriction_id == MovementRestriction.id,
        )
        .join(
            InjuryType, InjuryType.id == injury_movement_restrictions.c.injury_type_id
        )
        .join(UserInjury, UserInjury.injury_type_id == InjuryType.id)
        .where(
            UserInjury.user_id == user_id,
            UserInjury.is_active == True,  # noqa: E712
        )
    )
    restrictions = []
    for restriction, severity, injury_name in result.all():
        if SEVERITY_ORDER.get(severity, 1) >= SEVERITY_ORDER.get(
            restriction.severity_threshold, 0
        ):
            restrictions.append(
                {
                    "type": restriction.restriction_type,
                    "value": restriction.restriction_value,
                    "injury_name": injury_name,
                }
            )
    return restrictions


def _injury_reason(exercise: Exercise, restrictions: list[dict]) -> str | None:
    """Conservative match: any restriction hit excludes the exercise."""
    fields = {
        "movement_pattern": [
            exercise.movement_pattern_1,
            exercise.movement_pattern_2,
            exercise.movement_pattern_3,
        ],
        "force_type": [exercise.force_type],
        "plane_of_motion": [
            exercise.plane_of_motion_1,
            exercise.plane_of_motion_2,
            exercise.plane_of_motion_3,
        ],
        "posture": [exercise.posture],
    }
    for r in restrictions:
        values = [v.lower() for v in fields.get(r["type"], []) if v]
        if r["value"].lower() in values:
            return f"May aggravate {r['injury_name']} (not medical advice - consult a healthcare professional)"
    return None


async def _available_equipment_ids(db: AsyncSession, user_id: int) -> set[int] | None:
    """Equipment ids from the user's default profile; None = no profile (allow all)."""
    result = await db.execute(
        select(EquipmentProfile).where(
            EquipmentProfile.user_id == user_id,
            EquipmentProfile.is_default == True,  # noqa: E712
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return set(profile.equipment_ids or [])


async def _weekly_sets_by_muscle_group(
    db: AsyncSession, user_id: int
) -> dict[int, int]:
    """Completed sets this ISO week per muscle group id, from new tables."""
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(RoundEntry.exercise_id, EntrySet.id)
        .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
        .join(TrainingSession, TrainingSession.id == SupersetRound.session_id)
        .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.started_at >= week_start,
            EntrySet.completed == True,  # noqa: E712
        )
    )
    sets_per_exercise: dict[int, int] = defaultdict(int)
    for exercise_id, _set_id in result.all():
        sets_per_exercise[exercise_id] += 1
    if not sets_per_exercise:
        return {}

    # muscle_groups is eager-loaded: these exercises are whatever was logged
    # this week, which need not overlap the staple pool the caller already
    # loaded, and a lazy many-to-many access raises on an async session.
    counts: dict[int, int] = defaultdict(int)
    exercises = (
        (
            await db.execute(
                select(Exercise)
                .where(Exercise.id.in_(sets_per_exercise.keys()))
                .options(selectinload(Exercise.muscle_groups))
            )
        )
        .scalars()
        .all()
    )
    for exercise in exercises:
        for mg in exercise.muscle_groups:
            counts[mg.id] += sets_per_exercise[exercise.id]
    return dict(counts)


async def _filter_cards(
    db: AsyncSession,
    user_id: int,
    exercises: list[Exercise],
    pattern_by_exercise: dict[int, MovementPattern],
    staple_ids: set[int],
    rep_ranges: dict[int, tuple[int, int]],
) -> tuple[list[dict], list[dict]]:
    """Apply blacklist -> injury -> equipment -> weekly volume. Returns (cards, not_recommended)."""
    blacklist = await _blacklisted_ids(db, user_id)
    restrictions = await _injury_restrictions(db, user_id)
    available = await _available_equipment_ids(db, user_id)
    weekly = await _weekly_sets_by_muscle_group(db, user_id)
    last_map = await last_performed_map(db, user_id, [e.id for e in exercises])

    cards: list[dict] = []
    rejected: list[dict] = []
    for exercise in exercises:
        if exercise.id in blacklist:
            rejected.append(
                {
                    "exercise_name": exercise.name,
                    "reason": "Marked never (blacklisted in your preferences)",
                }
            )
            continue
        reason = _injury_reason(exercise, restrictions)
        if reason:
            rejected.append({"exercise_name": exercise.name, "reason": reason})
            continue
        is_bodyweight = exercise.primary_equipment_id is None
        if (
            not is_bodyweight
            and available is not None
            and exercise.primary_equipment_id not in available
        ):
            rejected.append(
                {
                    "exercise_name": exercise.name,
                    "reason": "Equipment not in your current profile",
                }
            )
            continue
        over = [
            mg
            for mg in exercise.muscle_groups
            if weekly.get(mg.id, 0) > WEEKLY_SET_LIMIT
        ]
        if over:
            rejected.append(
                {
                    "exercise_name": exercise.name,
                    "reason": f"Weekly volume exceeded for {over[0].name} (>{WEEKLY_SET_LIMIT} sets)",
                }
            )
            continue

        pattern = pattern_by_exercise[exercise.id]
        rep_min, rep_max = rep_ranges.get(pattern.id, (8, 12))
        cards.append(
            {
                "exercise_id": exercise.id,
                "exercise_name": exercise.name,
                "pattern_id": pattern.id,
                "pattern_slug": pattern.slug,
                "equipment_name": (
                    exercise.primary_equipment.name
                    if exercise.primary_equipment
                    else None
                ),
                "is_bodyweight": is_bodyweight,
                "last_performed": last_map.get(exercise.id),
                "is_staple": exercise.id in staple_ids,
                "target": await compute_entry_target(
                    db, user_id, exercise.id, rep_min, rep_max
                ),
            }
        )

    # Least-recently-performed first; never-performed (None) sorts first
    cards.sort(
        key=lambda c: (
            c["last_performed"] is not None,
            c["last_performed"] or datetime.min,
        )
    )
    return cards, _diverse_limit(rejected)


def _diverse_limit(rejected: list[dict], limit: int = 10) -> list[dict]:
    """Cap why-not entries at `limit`, spread across reason types.

    Diversity comes first: an even slice per reason type, so no single reason
    can crowd out the others. The result is then topped up round-robin from
    whatever each type has left, so an uneven spread of reasons doesn't
    short-change the list the user reads. Never exceeds `limit` and never
    repeats an entry.
    """
    by_reason: dict[str, list[dict]] = defaultdict(list)
    for entry in rejected:
        by_reason[entry["reason"].split("(")[0]].append(entry)

    buckets = list(by_reason.values())
    per_type = max(1, limit // max(1, len(buckets)))
    taken = [0] * len(buckets)
    diverse: list[dict] = []

    # Pass 1: even slice per reason type.
    for index, entries in enumerate(buckets):
        for entry in entries[:per_type]:
            if len(diverse) >= limit:
                return diverse
            diverse.append(entry)
            taken[index] += 1

    # Pass 2: round-robin top-up from what each type still has.
    while len(diverse) < limit:
        progressed = False
        for index, entries in enumerate(buckets):
            if taken[index] >= len(entries):
                continue
            diverse.append(entries[taken[index]])
            taken[index] += 1
            progressed = True
            if len(diverse) >= limit:
                return diverse
        if not progressed:
            break
    return diverse


async def _session_context(db: AsyncSession, user_id: int, session_id: int):
    """Load session, its goals (with rep ranges), and per-pattern completed set counts."""
    session = (
        await db.execute(
            select(TrainingSession).where(
                TrainingSession.id == session_id,
                TrainingSession.user_id == user_id,
            )
        )
    ).scalar_one()

    goals: list[PatternGoal] = []
    if session.day_plan_id:
        goals = (
            (
                await db.execute(
                    select(PatternGoal).where(
                        PatternGoal.day_plan_id == session.day_plan_id
                    )
                )
            )
            .scalars()
            .all()
        )

    sets_by_pattern: dict[int, int] = defaultdict(int)
    rows = (
        await db.execute(
            select(RoundEntry.pattern_id, EntrySet.id)
            .join(SupersetRound, SupersetRound.id == RoundEntry.round_id)
            .join(EntrySet, EntrySet.entry_id == RoundEntry.id)
            .where(
                SupersetRound.session_id == session_id,
                EntrySet.completed == True,  # noqa: E712
            )
        )
    ).all()
    for pattern_id, _sid in rows:
        sets_by_pattern[pattern_id] += 1

    rep_ranges = {
        g.pattern_id: (g.rep_range_min or 8, g.rep_range_max or 12) for g in goals
    }
    return session, goals, dict(sets_by_pattern), rep_ranges


def _goal_covered(goal: PatternGoal, sets_by_pattern: dict[int, int]) -> bool:
    target = goal.target_sets or 3
    return sets_by_pattern.get(goal.pattern_id, 0) >= target


async def _staples_with_exercises(
    db: AsyncSession, user_id: int, pattern_ids: list[int] | None
):
    """Active staples, with Exercise rows loaded.

    pattern_ids=None means every pattern - used by the free-form fallback,
    which has no goals to narrow the set down to.
    """
    query = select(StapleExercise).where(
        StapleExercise.user_id == user_id,
        StapleExercise.is_active == True,  # noqa: E712
    )
    if pattern_ids is not None:
        query = query.where(StapleExercise.pattern_id.in_(pattern_ids))
    result = await db.execute(
        query.options(
            selectinload(StapleExercise.exercise).selectinload(Exercise.muscle_groups),
            selectinload(StapleExercise.exercise).selectinload(
                Exercise.primary_equipment
            ),
            selectinload(StapleExercise.pattern),
        )
    )
    return result.scalars().all()


async def anchor_suggestions(db: AsyncSession, user_id: int, session_id: int) -> dict:
    """Staples grouped by the session's pattern goals, uncovered required goals first.

    A free-form session - no day plan, or a day plan with no pattern goals -
    has no coverage to chase, so it falls back to every pattern the user has
    active staples for, in taxonomy display order, all reported uncovered.
    """
    session, goals, sets_by_pattern, rep_ranges = await _session_context(
        db, user_id, session_id
    )

    if goals:
        ordered_goals = sorted(
            goals,
            key=lambda g: (_goal_covered(g, sets_by_pattern), not g.required),
        )
        staples = await _staples_with_exercises(
            db, user_id, [g.pattern_id for g in ordered_goals]
        )
        ordered_patterns = [
            (g.pattern_id, _goal_covered(g, sets_by_pattern)) for g in ordered_goals
        ]
    else:
        staples = await _staples_with_exercises(db, user_id, None)
        patterns_seen: dict[int, MovementPattern] = {}
        for staple in staples:
            patterns_seen.setdefault(staple.pattern_id, staple.pattern)
        ordered_patterns = [
            (pattern_id, False)
            for pattern_id, pattern in sorted(
                patterns_seen.items(),
                key=lambda item: (item[1].display_order, item[1].id),
            )
        ]

    staples_by_pattern: dict[int, list] = defaultdict(list)
    for staple in staples:
        staples_by_pattern[staple.pattern_id].append(staple)

    groups = []
    all_rejected: list[dict] = []
    for pattern_id, covered in ordered_patterns:
        pattern_staples = staples_by_pattern.get(pattern_id, [])
        if not pattern_staples:
            continue
        pattern = pattern_staples[0].pattern
        exercises = [s.exercise for s in pattern_staples]
        pattern_by_exercise = {s.exercise_id: s.pattern for s in pattern_staples}
        staple_ids = {s.exercise_id for s in pattern_staples}
        cards, rejected = await _filter_cards(
            db, user_id, exercises, pattern_by_exercise, staple_ids, rep_ranges
        )
        all_rejected.extend(rejected)
        groups.append(
            {
                "pattern": {
                    "id": pattern.id,
                    "slug": pattern.slug,
                    "name": pattern.name,
                },
                "covered": covered,
                "staples": cards,
            }
        )
    return {"groups": groups, "not_recommended": _diverse_limit(all_rejected)}


async def partner_suggestions(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    anchor_exercise_id: int,
    position: int,
) -> dict:
    """Partner candidates for a superset entry.

    position 2: opposite pattern of the anchor's pattern.
    position 3: neutral patterns plus any uncovered goals (never the anchor's pair).
    """
    session, goals, sets_by_pattern, rep_ranges = await _session_context(
        db, user_id, session_id
    )

    anchor_map = (
        await db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == anchor_exercise_id
            )
        )
    ).scalar_one()
    anchor_pattern = (
        await db.execute(
            select(MovementPattern).where(MovementPattern.id == anchor_map.pattern_id)
        )
    ).scalar_one()

    if position == 2:
        if anchor_pattern.opposite_pattern_id is None:
            # Neutral anchor: fall back to uncovered goals
            target_pattern_ids = [
                g.pattern_id for g in goals if not _goal_covered(g, sets_by_pattern)
            ]
        else:
            target_pattern_ids = [anchor_pattern.opposite_pattern_id]
    else:  # position == 3
        neutral_ids = [
            p.id
            for p in (
                await db.execute(
                    select(MovementPattern).where(
                        MovementPattern.is_neutral == True,  # noqa: E712
                    )
                )
            )
            .scalars()
            .all()
        ]
        pair_ids = {anchor_pattern.id, anchor_pattern.opposite_pattern_id}
        uncovered = [
            g.pattern_id
            for g in goals
            if not _goal_covered(g, sets_by_pattern) and g.pattern_id not in pair_ids
        ]
        target_pattern_ids = list(dict.fromkeys(neutral_ids + uncovered))

    staples = await _staples_with_exercises(db, user_id, target_pattern_ids)
    # The anchor is never its own partner. It can reach the target set when it
    # is neutral (its own pattern is in the neutral list at position 3, or is
    # an uncovered goal at position 2), so screen it out explicitly.
    exercises = [s.exercise for s in staples if s.exercise_id != anchor_exercise_id]
    pattern_by_exercise = {s.exercise_id: s.pattern for s in staples}
    staple_ids = {s.exercise_id for s in staples}
    cards, rejected = await _filter_cards(
        db, user_id, exercises, pattern_by_exercise, staple_ids, rep_ranges
    )

    novelty = await _novelty_candidate(
        db, user_id, target_pattern_ids, staple_ids | {anchor_exercise_id}, rep_ranges
    )
    return {"candidates": cards, "novelty": novelty, "not_recommended": rejected}


async def _novelty_candidate(
    db: AsyncSession,
    user_id: int,
    pattern_ids: list[int],
    exclude_ids: set[int],
    rep_ranges: dict[int, tuple[int, int]],
) -> dict | None:
    """One 'try something new' compound.

    Matches the target pattern, is not excluded (staples and the anchor
    itself), and passes the same blacklist, injury, equipment and weekly
    volume filters the staple candidates do - an unfamiliar exercise for a
    muscle group already past its weekly limit is worse than a familiar one,
    not better. Also skips anything performed in the last
    NOVELTY_STALENESS_DAYS.
    """
    blacklist = await _blacklisted_ids(db, user_id)
    available = await _available_equipment_ids(db, user_id)
    restrictions = await _injury_restrictions(db, user_id)
    weekly = await _weekly_sets_by_muscle_group(db, user_id)

    # Exclusions that can be expressed in SQL are, so the row cap applies to
    # genuine candidates rather than being spent on staples and blacklisted
    # rows. The ordering rotates weekly: deterministic within a week (so the
    # pick is stable for a user mid-session and for tests), but shifted across
    # the id space week to week so the same lowest-id row isn't pinned
    # forever.
    skip_ids = exclude_ids | blacklist
    rotation = date.today().isocalendar()[1]
    order_key = (Exercise.id * NOVELTY_ROTATION_STRIDE + rotation) % (
        NOVELTY_ROTATION_MODULUS
    )
    query = (
        select(Exercise, ExercisePatternMap.pattern_id)
        .join(ExercisePatternMap, ExercisePatternMap.exercise_id == Exercise.id)
        .where(
            ExercisePatternMap.pattern_id.in_(pattern_ids),
            Exercise.mechanics == "Compound",
        )
        .options(
            selectinload(Exercise.primary_equipment),
            selectinload(Exercise.muscle_groups),
        )
        .order_by(order_key, Exercise.id)
        .limit(NOVELTY_SCAN_LIMIT)
    )
    if skip_ids:
        query = query.where(Exercise.id.notin_(skip_ids))
    result = await db.execute(query)
    rows = result.all()
    if not rows:
        return None
    last_map = await last_performed_map(db, user_id, [e.id for e, _p in rows])
    cutoff = datetime.utcnow() - timedelta(days=NOVELTY_STALENESS_DAYS)
    patterns = {
        p.id: p
        for p in (
            await db.execute(
                select(MovementPattern).where(MovementPattern.id.in_(pattern_ids))
            )
        )
        .scalars()
        .all()
    }

    for exercise, pattern_id in rows:
        if _injury_reason(exercise, restrictions):
            continue
        is_bodyweight = exercise.primary_equipment_id is None
        if (
            not is_bodyweight
            and available is not None
            and exercise.primary_equipment_id not in available
        ):
            continue
        if any(
            weekly.get(mg.id, 0) > WEEKLY_SET_LIMIT for mg in exercise.muscle_groups
        ):
            continue
        last = last_map.get(exercise.id)
        if last is not None and last > cutoff:
            continue
        pattern = patterns[pattern_id]
        rep_min, rep_max = rep_ranges.get(pattern_id, (8, 12))
        return {
            "exercise_id": exercise.id,
            "exercise_name": exercise.name,
            "pattern_id": pattern_id,
            "pattern_slug": pattern.slug,
            "equipment_name": (
                exercise.primary_equipment.name if exercise.primary_equipment else None
            ),
            "is_bodyweight": is_bodyweight,
            "last_performed": last,
            "is_staple": False,
            "target": await compute_entry_target(
                db, user_id, exercise.id, rep_min, rep_max
            ),
        }
    return None
