"""Map a pulled Hevy workout history onto SlotFit staples.

The two exercise catalogues do not align: Hevy is often less specific than
SlotFit (one Hevy title, several SlotFit candidates), and SlotFit's catalogue
has no gym machines at all. See
docs/superpowers/specs/2026-08-02-hevy-staple-seeding-design.md.

This module holds the logic; backend/scripts/hevy_staples.py is the CLI.
"""

from __future__ import annotations

import copy
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

import yaml
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Equipment,
    Exercise,
    ExercisePatternMap,
    MovementPattern,
    StapleExercise,
    User,
)
from app.models.exercise import exercise_muscle_groups

# Hevy's equipment vocabulary is five values wide. SlotFit has 39 named
# implements and no typology. "machine" is deliberately mapped to None: it is
# both over-broad and wrong in practice (Hevy tags Pull Up and Chin Up with it),
# so it must never influence scoring in either direction.
HEVY_EQUIPMENT_ALIASES: dict[str, str | None] = {
    "barbell": "Barbell",
    "dumbbell": "Dumbbell",
    "kettlebell": "Kettlebell",
    "none": "Bodyweight",
    "machine": None,
}

# Gym machines SlotFit's functional-fitness catalogue lacks entirely. Named as
# specific implements to match the existing convention (Trap Bar, EZ Bar,
# Landmine) rather than one generic "Machine" bucket.
MACHINE_EQUIPMENT: tuple[tuple[str, str], ...] = (
    ("Rowing Machine", "Machine"),
    ("Leg Press Machine", "Machine"),
    ("Hack Squat Machine", "Machine"),
    ("Chest Press Machine", "Machine"),
    ("Pec Deck", "Machine"),
    ("Hyperextension Bench", "Machine"),
)

STOP_TOKENS = frozenset({"the", "a", "of", "and", "with"})


def normalize_tokens(name: str) -> set[str]:
    """Reduce an exercise name to a comparable token set.

    Parentheticals are unwrapped rather than dropped, so the equipment hint in
    "Incline Bench Press (Dumbbell)" survives. Trailing plurals are folded on
    tokens longer than three characters so "triceps" and "tricep" unify.
    """
    unwrapped = re.sub(r"\(([^)]*)\)", r" \1 ", name.lower())
    tokens = set()
    for token in re.split(r"[^a-z0-9]+", unwrapped):
        if not token or token in STOP_TOKENS:
            continue
        if len(token) > 3 and token.endswith("s"):
            token = token[:-1]
        tokens.add(token)
    return tokens


def slotfit_equipment_for(hevy_equipment: str | None) -> str | None:
    """Return the SlotFit equipment name for a Hevy equipment value.

    None means "unknown" - either Hevy said "machine" (uninformative) or the
    value is one we do not model. Callers must treat None as neutral, never as
    a mismatch.
    """
    if hevy_equipment is None:
        return None
    return HEVY_EQUIPMENT_ALIASES.get(hevy_equipment)


@dataclass(frozen=True)
class HevyExercise:
    """One exercise the user actually performed, within the selection window."""

    title: str
    template_id: str | None
    sessions: int
    last_performed: str
    hevy_equipment: str | None


def _parse_start(workout: dict) -> datetime | None:
    raw = (workout.get("start_time") or "").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def select_exercises(
    workouts: list[dict],
    templates: dict[str, dict],
    window_days: int = 365,
    min_sessions: int = 3,
) -> list[HevyExercise]:
    """Pick the exercises that define the staple pool.

    The window is measured back from the most recent workout, not from today,
    so a stale export still yields the same answer. An exercise appearing twice
    in one workout counts as one session.

    Returns entries sorted by session count descending, so review effort lands
    on the exercises that matter most first.
    """
    dated = [(start, w) for w in workouts if (start := _parse_start(w)) is not None]
    if not dated:
        return []
    cutoff = max(start for start, _ in dated) - timedelta(days=window_days)

    sessions: Counter[str] = Counter()
    template_id: dict[str, str | None] = {}
    last_seen: dict[str, datetime] = {}
    for start, workout in dated:
        if start < cutoff:
            continue
        for entry in workout.get("exercises") or []:
            if entry.get("title") is not None:
                template_id.setdefault(entry["title"], entry.get("exercise_template_id"))
        for title in {e.get("title") for e in (workout.get("exercises") or [])}:
            if title is None:
                continue
            sessions[title] += 1
            if title not in last_seen or start > last_seen[title]:
                last_seen[title] = start

    selected = []
    for title, count in sessions.items():
        if count < min_sessions:
            continue
        tid = template_id.get(title)
        selected.append(
            HevyExercise(
                title=title,
                template_id=tid,
                sessions=count,
                last_performed=last_seen[title].date().isoformat(),
                hevy_equipment=(templates.get(tid) or {}).get("equipment"),
            )
        )
    selected.sort(key=lambda e: (-e.sessions, e.title))
    return selected


EQUIPMENT_AGREEMENT_BONUS = 0.15
EQUIPMENT_CONTRADICTION_PENALTY = 0.25


@dataclass(frozen=True)
class CatalogueEntry:
    """One SlotFit exercise, reduced to what matching needs."""

    name: str
    equipment: str | None


@dataclass(frozen=True)
class Ranked:
    """A scored SlotFit candidate for one Hevy exercise."""

    name: str
    recall: float
    score: float


def rank_candidates(
    hevy: HevyExercise,
    catalogue: Sequence[CatalogueEntry],
    limit: int = 5,
) -> list[Ranked]:
    """Rank SlotFit exercises as candidates for one Hevy exercise.

    Token recall dominates. Equipment adjusts, but only when Hevy's value is
    informative - "machine" is neutral. A length penalty keeps
    "Dumbbell Pullover" ahead of "Stability Ball Double Dumbbell Seated
    Pullover" at equal recall.
    """
    hevy_tokens = normalize_tokens(hevy.title)
    if not hevy_tokens:
        return []
    want = slotfit_equipment_for(hevy.hevy_equipment)

    scored: list[tuple[float, float, int, str]] = []
    for entry in catalogue:
        entry_tokens = normalize_tokens(entry.name)
        overlap = len(hevy_tokens & entry_tokens)
        if not overlap:
            continue
        recall = overlap / len(hevy_tokens)
        score = recall
        if want is not None:
            score += (
                EQUIPMENT_AGREEMENT_BONUS
                if entry.equipment == want
                else -EQUIPMENT_CONTRADICTION_PENALTY
            )
        scored.append((score, recall, len(entry_tokens), entry.name))

    # Best score first; then the shorter name, so "Dumbbell Pullover" beats
    # "Stability Ball Double Dumbbell Seated Pullover"; then name for a stable
    # order when everything else ties.
    scored.sort(key=lambda row: (-row[0], row[2], row[3]))
    return [
        Ranked(name=name, recall=recall, score=score)
        for score, recall, _, name in scored[:limit]
    ]


def should_prefill(ranked: Sequence[Ranked]) -> bool:
    """True only when the top candidate is unambiguously correct.

    Requires full token recall and a strictly-best score. Measured against real
    data this fires on about 1 entry in 58, which is the honest shape of the
    problem rather than a tuning failure: most Hevy titles genuinely match
    several SlotFit exercises that differ only by grip or stance.
    """
    if not ranked:
        return False
    top = ranked[0]
    if top.recall < 1.0:
        return False
    return len(ranked) == 1 or ranked[1].score < top.score


MAP_HEADER = """\
# Hevy to SlotFit exercise mapping.
#
# Generated by: python -m scripts.hevy_staples generate
# Applied by:   python -m scripts.hevy_staples apply --commit
#
# Resolve every entry exactly one of three ways:
#
#   slotfit: Cable V Grip Lat Pulldown   an existing SlotFit exercise, by name
#   slotfit: 2                           the 2nd listed candidate, by index
#   slotfit: SKIP                        not a real exercise (e.g. "Rest")
#   create: {name: ..., pattern: ..., equipment: ...}
#                                        SlotFit has no equivalent; make one
#
# Entries are ordered most-performed first. `candidates` is advisory - the
# generator only pre-fills `slotfit` when exactly one candidate is
# unambiguously correct, which is rare by design.
"""


def build_map_document(
    exercises: Sequence[HevyExercise],
    catalogue: Sequence[CatalogueEntry],
    generated_at: str,
    window_days: int = 365,
    min_sessions: int = 3,
) -> dict:
    """Build the reviewable mapping document for the selected exercises."""
    rows = []
    for exercise in exercises:
        ranked = rank_candidates(exercise, catalogue)
        rows.append(
            {
                "hevy": exercise.title,
                "hevy_template_id": exercise.template_id,
                "sessions": exercise.sessions,
                "last_performed": exercise.last_performed,
                "hevy_equipment": exercise.hevy_equipment,
                "slotfit": ranked[0].name if should_prefill(ranked) else None,
                "candidates": [r.name for r in ranked],
            }
        )
    return {
        "meta": {
            "generated_from": "hevy/data/workouts.json",
            "generated_at": generated_at,
            "window_days": window_days,
            "min_sessions": min_sessions,
        },
        "exercises": rows,
    }


def dump_map(document: dict) -> str:
    """Serialize the mapping document to YAML, with review instructions on top."""
    body = yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=100)
    return f"{MAP_HEADER}\n{body}"


SKIP = "SKIP"


def variant_name_for(base_name: str, variant_type: str) -> str:
    """Name a variant the way POST /exercises/{id}/variants already does."""
    return f"{base_name} ({variant_type})"


def resolve_selection(raw: object, candidates: Sequence[str]) -> str | None:
    """Turn a reviewed `slotfit:` value into an exercise name.

    Accepts a 1-based candidate index so a review decision is one keystroke,
    an exact exercise name, or the SKIP sentinel. Returns None when the entry
    is still unresolved. An out-of-range index returns None so validate_map
    reports it rather than silently selecting the wrong exercise.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        if 1 <= raw <= len(candidates):
            return candidates[raw - 1]
        return None
    text = str(raw).strip()
    return text or None


def validate_map(
    document: dict,
    known_exercises: set[str],
    known_patterns: set[str],
    known_equipment: set[str],
    custom_exercises: set[str] | None = None,
) -> list[str]:
    """Check a reviewed mapping document, returning every problem at once.

    Reporting all errors together matters: the reviewer resolves ~58 entries by
    hand, and fixing them one failed run at a time would be miserable.

    `custom_exercises` are exercises a previous apply created (is_custom). A
    create block naming one of those is a re-run, not a mistake, so it passes -
    apply reuses the row. A create block naming a *stock* catalogue exercise is
    still an error, because that entry should have used `slotfit:` instead.
    """
    custom_exercises = custom_exercises or set()
    errors: list[str] = []
    for row in document.get("exercises") or []:
        label = row.get("hevy", "<unnamed>")
        raw = row.get("slotfit")
        candidates = row.get("candidates") or []
        create = row.get("create")

        if create is not None and raw is not None:
            errors.append(f"{label}: sets both 'slotfit' and 'create' - choose one")
            continue

        if create is not None:
            base = create.get("variant_of")
            pattern = create.get("pattern")
            equipment = create.get("equipment")

            if base:
                # A variant inherits the base's pattern, muscles, and equipment,
                # so declaring a pattern here would be silently ignored.
                variant_type = (create.get("variant_type") or "").strip()
                if base not in known_exercises:
                    errors.append(f"{label}: variant_of names no such exercise {base!r}")
                if not variant_type:
                    errors.append(f"{label}: variant_of needs a 'variant_type'")
                if pattern:
                    errors.append(
                        f"{label}: a variant takes its pattern from its base - "
                        f"remove 'pattern'"
                    )
                if variant_type and base in known_exercises:
                    derived = variant_name_for(base, variant_type)
                    if derived in known_exercises and derived not in custom_exercises:
                        errors.append(
                            f"{label}: variant {derived!r} already exists in the catalogue"
                        )
                continue

            name = (create.get("name") or "").strip()
            if not name:
                errors.append(f"{label}: create needs a 'name'")
            elif name in known_exercises and name not in custom_exercises:
                errors.append(
                    f"{label}: create name {name!r} already exists in the catalogue"
                )
            if not pattern:
                errors.append(f"{label}: create needs a 'pattern' slug")
            elif pattern not in known_patterns:
                errors.append(f"{label}: unknown pattern {pattern!r}")
            if equipment is not None and equipment not in known_equipment:
                errors.append(f"{label}: unknown equipment {equipment!r}")
            continue

        if isinstance(raw, int) and not isinstance(raw, bool):
            if not 1 <= raw <= len(candidates):
                errors.append(
                    f"{label}: candidate index {raw} is out of range "
                    f"(1-{len(candidates)})"
                )
                continue

        resolved = resolve_selection(raw, candidates)
        if resolved is None:
            errors.append(f"{label}: unresolved - set 'slotfit' or 'create'")
        elif resolved != SKIP and resolved not in known_exercises:
            errors.append(f"{label}: unknown SlotFit exercise {resolved!r}")
    return errors


def apply_review_selections(document: dict, selections: dict[str, dict]) -> dict:
    """Fold review decisions into a mapping document, returning a new document.

    `selections` maps a Hevy exercise title to one of:
        {"kind": "exercise", "name": ...}
        {"kind": "skip"}
        {"kind": "create", "name": ..., "pattern": ..., "equipment": ...}

    Entries with no selection are left exactly as they were, so a partial
    review can be saved and resumed. The input document is not mutated.
    """
    result = copy.deepcopy(document)
    for row in result.get("exercises") or []:
        choice = selections.get(row.get("hevy"))
        if choice is None:
            continue

        kind = choice.get("kind")
        if kind == "variant":
            create = {
                "variant_of": choice.get("variant_of"),
                "variant_type": (choice.get("variant_type") or "").strip(),
            }
            duration = str(choice.get("default_time_seconds") or "").strip()
            if duration:
                create["default_time_seconds"] = int(duration)
            row["create"] = create
            row["slotfit"] = None
            continue

        if kind == "create":
            create = {
                "name": (choice.get("name") or "").strip(),
                "pattern": choice.get("pattern"),
            }
            equipment = (choice.get("equipment") or "").strip()
            if equipment:
                create["equipment"] = equipment
            row["create"] = create
            row["slotfit"] = None
            continue

        # Any non-create choice supersedes a create block left from an earlier pass.
        row.pop("create", None)
        row["slotfit"] = SKIP if kind == "skip" else (choice.get("name") or "").strip()
    return result


@dataclass
class ApplyResult:
    """Counts from one apply run, for the CLI to report."""

    equipment_created: int = 0
    exercises_created: int = 0
    staples_created: int = 0
    skipped_existing: int = 0
    skipped_no_pattern: int = 0
    skipped_explicit: int = 0


async def _ensure_machine_equipment(db: AsyncSession) -> int:
    """Insert the six machine equipment rows if absent. Returns rows created."""
    existing = set((await db.execute(select(Equipment.name))).scalars().all())
    created = 0
    for name, category in MACHINE_EQUIPMENT:
        if name in existing:
            continue
        db.add(Equipment(name=name, category=category))
        created += 1
    if created:
        await db.flush()
    return created


async def _create_variant(db: AsyncSession, base_name: str, create: dict) -> int:
    """Create a training-style variant of an existing exercise. Returns its id.

    Mirrors POST /exercises/{id}/variants: the variant copies the base's
    descriptive attributes and muscle groups so pattern coverage and antagonist
    pairing keep working, and is linked back via base_exercise_id. What differs
    is the training intent - variant_type and a time-based default.
    """
    base = (
        await db.execute(select(Exercise).where(Exercise.name == base_name))
    ).scalar_one()

    variant = Exercise(
        name=variant_name_for(base_name, create["variant_type"]),
        description=base.description,
        exercise_classification=base.exercise_classification,
        primary_equipment_id=base.primary_equipment_id,
        secondary_equipment_id=base.secondary_equipment_id,
        primary_equipment_count=base.primary_equipment_count,
        secondary_equipment_count=base.secondary_equipment_count,
        posture=base.posture,
        movement_pattern_1=base.movement_pattern_1,
        movement_pattern_2=base.movement_pattern_2,
        movement_pattern_3=base.movement_pattern_3,
        plane_of_motion_1=base.plane_of_motion_1,
        body_region=base.body_region,
        force_type=base.force_type,
        mechanics=base.mechanics,
        laterality=base.laterality,
        difficulty=base.difficulty,
        base_exercise_id=base.id,
        variant_type=create["variant_type"],
        is_custom="True",
        default_time_seconds=create.get("default_time_seconds"),
    )
    db.add(variant)
    await db.flush()

    for muscle_group in await _base_muscle_groups(db, base.id):
        await db.execute(
            insert(exercise_muscle_groups).values(
                exercise_id=variant.id,
                muscle_group_id=muscle_group.muscle_group_id,
                role=muscle_group.role,
            )
        )

    # Inherit the base's pattern rather than re-classifying: a HIIT reverse fly
    # is still the same movement. is_override protects it from seed_patterns.
    base_map = (
        await db.execute(
            select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == base.id)
        )
    ).scalar_one_or_none()
    if base_map is not None:
        db.add(
            ExercisePatternMap(
                exercise_id=variant.id,
                pattern_id=base_map.pattern_id,
                is_override=True,
            )
        )
    await db.flush()
    return variant.id


async def _base_muscle_groups(db: AsyncSession, base_id: int):
    """Rows of (muscle_group_id, role) for an exercise, straight from the join table."""
    return (
        await db.execute(
            select(
                exercise_muscle_groups.c.muscle_group_id,
                exercise_muscle_groups.c.role,
            ).where(exercise_muscle_groups.c.exercise_id == base_id)
        )
    ).all()


async def apply_map(db: AsyncSession, document: dict, user: User) -> ApplyResult:
    """Seed staples for one user from a validated mapping document.

    Additive and idempotent: existing staples, exercises, and equipment rows are
    reused, never updated or deleted. Running twice creates nothing the second
    time.

    Validate with validate_map before calling. The caller owns the commit.
    """
    result = ApplyResult()
    result.equipment_created = await _ensure_machine_equipment(db)

    equipment_ids = {
        name: eid
        for eid, name in (await db.execute(select(Equipment.id, Equipment.name))).all()
    }
    pattern_ids = {
        slug: pid
        for pid, slug in (
            await db.execute(select(MovementPattern.id, MovementPattern.slug))
        ).all()
    }
    exercise_ids = {
        name: eid
        for eid, name in (await db.execute(select(Exercise.id, Exercise.name))).all()
    }
    existing_staples = set(
        (
            await db.execute(
                select(StapleExercise.exercise_id).where(
                    StapleExercise.user_id == user.id
                )
            )
        )
        .scalars()
        .all()
    )

    for row in document.get("exercises") or []:
        create = row.get("create")

        if create is not None:
            base_name = create.get("variant_of")
            if base_name:
                name = variant_name_for(base_name, create["variant_type"])
            else:
                name = create["name"].strip()

            exercise_id = exercise_ids.get(name)
            if exercise_id is None:
                if base_name:
                    exercise_id = await _create_variant(db, base_name, create)
                else:
                    equipment_name = create.get("equipment")
                    exercise = Exercise(
                        name=name,
                        is_custom="True",
                        primary_equipment_id=(
                            equipment_ids.get(equipment_name) if equipment_name else None
                        ),
                    )
                    db.add(exercise)
                    await db.flush()
                    exercise_id = exercise.id
                    # is_override keeps seed_exercise_pattern_map from rewriting
                    # the hand-assigned pattern on its next run.
                    db.add(
                        ExercisePatternMap(
                            exercise_id=exercise_id,
                            pattern_id=pattern_ids[create["pattern"]],
                            is_override=True,
                        )
                    )
                    await db.flush()
                exercise_ids[name] = exercise_id
                result.exercises_created += 1
        else:
            resolved = resolve_selection(row.get("slotfit"), row.get("candidates") or [])
            if resolved == SKIP:
                result.skipped_explicit += 1
                continue
            exercise_id = exercise_ids.get(resolved) if resolved else None
            if exercise_id is None:
                result.skipped_no_pattern += 1
                continue

        if exercise_id in existing_staples:
            result.skipped_existing += 1
            continue

        mapping = (
            await db.execute(
                select(ExercisePatternMap).where(
                    ExercisePatternMap.exercise_id == exercise_id
                )
            )
        ).scalar_one_or_none()
        if mapping is None:
            result.skipped_no_pattern += 1
            continue

        db.add(
            StapleExercise(
                user_id=user.id,
                pattern_id=mapping.pattern_id,
                exercise_id=exercise_id,
            )
        )
        existing_staples.add(exercise_id)
        result.staples_created += 1

    await db.flush()
    return result
