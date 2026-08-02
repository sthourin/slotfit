"""Map a pulled Hevy workout history onto SlotFit staples.

The two exercise catalogues do not align: Hevy is often less specific than
SlotFit (one Hevy title, several SlotFit candidates), and SlotFit's catalogue
has no gym machines at all. See
docs/superpowers/specs/2026-08-02-hevy-staple-seeding-design.md.

This module holds the logic; backend/scripts/hevy_staples.py is the CLI.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

import yaml

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
