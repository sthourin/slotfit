"""Map a pulled Hevy workout history onto SlotFit staples.

The two exercise catalogues do not align: Hevy is often less specific than
SlotFit (one Hevy title, several SlotFit candidates), and SlotFit's catalogue
has no gym machines at all. See
docs/superpowers/specs/2026-08-02-hevy-staple-seeding-design.md.

This module holds the logic; backend/scripts/hevy_staples.py is the CLI.
"""

from __future__ import annotations

import re

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
