# Hevy Staple Seeding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed a user's SlotFit staple pool from a pulled Hevy workout history, via a human-reviewed mapping file that resolves the two catalogues' incompatible exercise naming.

**Architecture:** Pure logic lives in `app/services/hevy_import.py` and is unit-tested without a database. A thin CLI at `scripts/hevy_staples.py` provides `generate` (writes a YAML mapping file of ranked candidates) and `apply` (validates the reviewed file, then writes equipment, custom exercises, and staples). This mirrors the existing `seed_patterns.py` / `pattern_taxonomy.py` split.

**Tech Stack:** Python 3.11, SQLAlchemy async, pytest with an in-memory SQLite fixture (`test_db`), PyYAML.

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-08-02-hevy-staple-seeding-design.md`. Read it before starting.
- Selection window: last 365 days, exercises performed in 3 or more sessions.
- Never auto-resolve an ambiguous exercise match. Pre-fill only on full token recall, no equipment contradiction, and a strictly-best top candidate.
- Hevy `machine` equipment is unreliable: never a bonus, never a contradiction.
- Hevy `none` equipment maps to the `Bodyweight` equipment row, **not** to a NULL `primary_equipment_id`. No exercise in this database has NULL equipment.
- All writes are additive and idempotent. Never update or delete an existing row.
- Created exercises get `is_custom="True"` (a String column, not Boolean) and an `ExercisePatternMap` row with `is_override=True`.
- Run all commands from `backend/`. Tests: `./venv/Scripts/python.exe -m pytest`.
- Commit subjects are prefixed `[SH]`.

---

### Task 1: Normalization and equipment vocabulary

**Files:**
- Create: `backend/app/services/hevy_import.py`
- Create: `backend/tests/test_hevy_import.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `normalize_tokens(name: str) -> set[str]`, `slotfit_equipment_for(hevy_equipment: str | None) -> str | None`, `HEVY_EQUIPMENT_ALIASES: dict[str, str | None]`, `MACHINE_EQUIPMENT: tuple[tuple[str, str], ...]`.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for the Hevy import service (backend/app/services/hevy_import.py)."""

import pytest

from app.services.hevy_import import (
    MACHINE_EQUIPMENT,
    normalize_tokens,
    slotfit_equipment_for,
)


def test_normalize_unwraps_parentheticals():
    assert normalize_tokens("Incline Bench Press (Dumbbell)") == {
        "incline", "bench", "pres", "dumbbell",
    }


def test_normalize_folds_plurals_over_three_chars():
    # "triceps" and "tricep" must unify; short tokens are left alone
    assert normalize_tokens("Triceps") == normalize_tokens("Tricep")
    assert "abs" in normalize_tokens("Abs Crunch")


def test_normalize_strips_punctuation_and_stopwords():
    assert normalize_tokens("Seated Cable Row - V Grip (Cable)") == {
        "seated", "cable", "row", "v", "grip",
    }


def test_equipment_aliases_map_known_values():
    assert slotfit_equipment_for("dumbbell") == "Dumbbell"
    assert slotfit_equipment_for("barbell") == "Barbell"
    assert slotfit_equipment_for("kettlebell") == "Kettlebell"


def test_bodyweight_maps_to_the_bodyweight_row_not_null():
    # The database has zero NULL primary_equipment_id rows; bodyweight is a real row.
    assert slotfit_equipment_for("none") == "Bodyweight"


def test_machine_is_unknown_not_a_value():
    # Hevy tags Pull Up and Chin Up as "machine"; the tag carries no information.
    assert slotfit_equipment_for("machine") is None
    assert slotfit_equipment_for(None) is None
    assert slotfit_equipment_for("something-new") is None


def test_machine_equipment_rows_are_specific_implements():
    names = [name for name, _ in MACHINE_EQUIPMENT]
    assert names == [
        "Rowing Machine",
        "Leg Press Machine",
        "Hack Squat Machine",
        "Chest Press Machine",
        "Pec Deck",
        "Hyperextension Bench",
    ]
    assert {category for _, category in MACHINE_EQUIPMENT} == {"Machine"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: FAIL, `ModuleNotFoundError: No module named 'app.services.hevy_import'`

- [ ] **Step 3: Write minimal implementation**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add app/services/hevy_import.py tests/test_hevy_import.py
git commit -m "[SH] feat: add Hevy name normalization and equipment vocabulary"
```

---

### Task 2: Select exercises from the workout history

**Files:**
- Modify: `backend/app/services/hevy_import.py`
- Modify: `backend/tests/test_hevy_import.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `HevyExercise` dataclass with fields `title: str`, `template_id: str | None`, `sessions: int`, `last_performed: str`, `hevy_equipment: str | None`; and `select_exercises(workouts: list[dict], templates: dict[str, dict], window_days: int = 365, min_sessions: int = 3) -> list[HevyExercise]` returning entries sorted by `sessions` descending then `title` ascending.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_hevy_import.py`:

```python
from app.services.hevy_import import HevyExercise, select_exercises


def _workout(start: str, titles: list[str]) -> dict:
    return {
        "start_time": start,
        "exercises": [
            {"exercise_template_id": f"tid-{t}", "title": t, "sets": [{}]} for t in titles
        ],
    }


TEMPLATES = {
    "tid-Bench": {"equipment": "dumbbell"},
    "tid-Row": {"equipment": "machine"},
    "tid-Old": {"equipment": "barbell"},
}


def test_selects_only_exercises_at_or_above_the_session_threshold():
    workouts = [
        _workout("2026-07-01T10:00:00Z", ["Bench", "Row"]),
        _workout("2026-07-02T10:00:00Z", ["Bench", "Row"]),
        _workout("2026-07-03T10:00:00Z", ["Bench"]),
    ]
    picked = {e.title for e in select_exercises(workouts, TEMPLATES, min_sessions=3)}
    assert picked == {"Bench"}


def test_window_excludes_older_workouts_relative_to_the_latest():
    workouts = [
        _workout("2023-01-01T10:00:00Z", ["Old"]),
        _workout("2023-01-02T10:00:00Z", ["Old"]),
        _workout("2023-01-03T10:00:00Z", ["Old"]),
        _workout("2026-07-03T10:00:00Z", ["Bench"]),
    ]
    picked = {e.title for e in select_exercises(workouts, TEMPLATES, min_sessions=1)}
    assert "Old" not in picked
    assert "Bench" in picked


def test_counts_sessions_not_set_occurrences():
    # Same exercise twice in one workout is one session, not two.
    workout = {
        "start_time": "2026-07-01T10:00:00Z",
        "exercises": [
            {"exercise_template_id": "tid-Bench", "title": "Bench", "sets": [{}]},
            {"exercise_template_id": "tid-Bench", "title": "Bench", "sets": [{}]},
        ],
    }
    (entry,) = select_exercises([workout], TEMPLATES, min_sessions=1)
    assert entry.sessions == 1


def test_carries_equipment_and_last_performed():
    workouts = [
        _workout("2026-07-01T10:00:00Z", ["Bench"]),
        _workout("2026-07-05T10:00:00Z", ["Bench"]),
    ]
    (entry,) = select_exercises(workouts, TEMPLATES, min_sessions=1)
    assert entry.hevy_equipment == "dumbbell"
    assert entry.last_performed == "2026-07-05"
    assert entry.template_id == "tid-Bench"


def test_sorted_by_session_count_descending():
    workouts = [
        _workout("2026-07-01T10:00:00Z", ["Bench", "Row"]),
        _workout("2026-07-02T10:00:00Z", ["Bench"]),
    ]
    titles = [e.title for e in select_exercises(workouts, TEMPLATES, min_sessions=1)]
    assert titles == ["Bench", "Row"]


def test_empty_history_returns_empty_list():
    assert select_exercises([], TEMPLATES) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: FAIL, `ImportError: cannot import name 'HevyExercise'`

- [ ] **Step 3: Write minimal implementation**

Add to the imports at the top of `app/services/hevy_import.py`:

```python
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
```

Then append:

```python
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
        for title in {e.get("title") for e in (workout.get("exercises") or [])}:
            if title is None:
                continue
            sessions[title] += 1
            if start > last_seen.get(title, cutoff - timedelta(days=1)):
                last_seen[title] = start
        for entry in workout.get("exercises") or []:
            if entry.get("title") is not None:
                template_id.setdefault(entry["title"], entry.get("exercise_template_id"))

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add app/services/hevy_import.py tests/test_hevy_import.py
git commit -m "[SH] feat: select Hevy staple candidates by window and session count"
```

---

### Task 3: Candidate ranking and the pre-fill gate

**Files:**
- Modify: `backend/app/services/hevy_import.py`
- Modify: `backend/tests/test_hevy_import.py`

**Interfaces:**
- Consumes: `normalize_tokens`, `slotfit_equipment_for`, `HevyExercise` from Tasks 1-2.
- Produces: `CatalogueEntry` dataclass with fields `name: str`, `equipment: str | None`; `Ranked` dataclass with fields `name: str`, `recall: float`, `score: float`; `rank_candidates(hevy: HevyExercise, catalogue: Sequence[CatalogueEntry], limit: int = 5) -> list[Ranked]`; `should_prefill(ranked: Sequence[Ranked]) -> bool`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_hevy_import.py`:

```python
from app.services.hevy_import import CatalogueEntry, rank_candidates, should_prefill


def _hevy(title: str, equipment: str | None = None) -> HevyExercise:
    return HevyExercise(
        title=title,
        template_id="tid",
        sessions=5,
        last_performed="2026-07-01",
        hevy_equipment=equipment,
    )


LAT_PULLDOWNS = [
    CatalogueEntry("Cable V Grip Lat Pulldown", "Cable"),
    CatalogueEntry("Cable Wide Grip Lat Pulldown", "Cable"),
    CatalogueEntry("Cable Reverse Grip Lat Pulldown", "Cable"),
    CatalogueEntry("Dumbbell Pullover", "Dumbbell"),
]


def test_ranks_by_token_recall():
    ranked = rank_candidates(_hevy("Wide Grip Lat Pulldown"), LAT_PULLDOWNS)
    assert ranked[0].name == "Cable Wide Grip Lat Pulldown"


def test_shorter_name_wins_on_equal_recall():
    catalogue = [
        CatalogueEntry("Stability Ball Double Dumbbell Seated Pullover", "Dumbbell"),
        CatalogueEntry("Dumbbell Pullover", "Dumbbell"),
    ]
    ranked = rank_candidates(_hevy("Pullover (Dumbbell)", "dumbbell"), catalogue)
    assert ranked[0].name == "Dumbbell Pullover"


def test_equipment_agreement_boosts_and_contradiction_penalises():
    catalogue = [
        CatalogueEntry("Kettlebell Goblet Squat", "Kettlebell"),
        CatalogueEntry("Dumbbell Goblet Squat", "Dumbbell"),
    ]
    ranked = rank_candidates(_hevy("Goblet Squat", "dumbbell"), catalogue)
    assert ranked[0].name == "Dumbbell Goblet Squat"


def test_machine_equipment_neither_boosts_nor_penalises():
    # Hevy calls a cable lat pulldown "machine". That must not demote Cable rows.
    ranked = rank_candidates(_hevy("Wide Grip Lat Pulldown", "machine"), LAT_PULLDOWNS)
    assert ranked[0].name == "Cable Wide Grip Lat Pulldown"


def test_limit_caps_the_candidate_list():
    assert len(rank_candidates(_hevy("Lat Pulldown"), LAT_PULLDOWNS, limit=2)) == 2


def test_no_overlap_yields_no_candidates():
    assert rank_candidates(_hevy("Rowing Machine"), LAT_PULLDOWNS) == []


def test_ambiguous_full_recall_must_not_prefill():
    # The heart of the design: three grips tie, so a human must choose.
    ranked = rank_candidates(_hevy("Lat Pulldown", "machine"), LAT_PULLDOWNS)
    assert ranked[0].recall == pytest.approx(1.0)
    assert should_prefill(ranked) is False


def test_unique_full_recall_prefills():
    catalogue = [
        CatalogueEntry("Dumbbell Goblet Squat", "Dumbbell"),
        CatalogueEntry("Barbell Back Squat", "Barbell"),
    ]
    ranked = rank_candidates(_hevy("Goblet Squat (Dumbbell)", "dumbbell"), catalogue)
    assert should_prefill(ranked) is True


def test_partial_recall_never_prefills():
    ranked = rank_candidates(_hevy("Iso-Lateral Chest Press"), [
        CatalogueEntry("Resistance Band Chest Press", "Resistance Band"),
    ])
    assert ranked and ranked[0].recall < 1.0
    assert should_prefill(ranked) is False


def test_empty_candidates_never_prefills():
    assert should_prefill([]) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: FAIL, `ImportError: cannot import name 'CatalogueEntry'`

- [ ] **Step 3: Write minimal implementation**

Add `from typing import Sequence` to the imports, then append:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: PASS, 23 tests

- [ ] **Step 5: Commit**

```bash
git add app/services/hevy_import.py tests/test_hevy_import.py
git commit -m "[SH] feat: rank Hevy exercise candidates and gate auto-prefill"
```

---

### Task 4: Build and serialize the mapping document

**Files:**
- Modify: `backend/app/services/hevy_import.py`
- Modify: `backend/tests/test_hevy_import.py`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Consumes: `HevyExercise`, `CatalogueEntry`, `rank_candidates`, `should_prefill`.
- Produces: `build_map_document(exercises: Sequence[HevyExercise], catalogue: Sequence[CatalogueEntry], generated_at: str, window_days: int = 365, min_sessions: int = 3) -> dict` and `dump_map(document: dict) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_hevy_import.py`:

```python
import yaml

from app.services.hevy_import import build_map_document, dump_map


CATALOGUE = [
    CatalogueEntry("Dumbbell Goblet Squat", "Dumbbell"),
    CatalogueEntry("Kettlebell Goblet Squat", "Kettlebell"),
    CatalogueEntry("Barbell Back Squat", "Barbell"),
]


def test_document_records_selection_meta():
    doc = build_map_document([], CATALOGUE, generated_at="2026-08-02")
    assert doc["meta"]["window_days"] == 365
    assert doc["meta"]["min_sessions"] == 3
    assert doc["meta"]["generated_at"] == "2026-08-02"


def test_unambiguous_entry_is_prefilled():
    entry = _hevy("Goblet Squat (Dumbbell)", "dumbbell")
    doc = build_map_document([entry], CATALOGUE, generated_at="2026-08-02")
    (row,) = doc["exercises"]
    assert row["slotfit"] == "Dumbbell Goblet Squat"


def test_ambiguous_entry_is_left_null_with_candidates():
    entry = _hevy("Goblet Squat", "machine")
    doc = build_map_document([entry], CATALOGUE, generated_at="2026-08-02")
    (row,) = doc["exercises"]
    assert row["slotfit"] is None
    assert "Dumbbell Goblet Squat" in row["candidates"]
    assert "Kettlebell Goblet Squat" in row["candidates"]


def test_entry_carries_review_context():
    entry = _hevy("Goblet Squat", "dumbbell")
    doc = build_map_document([entry], CATALOGUE, generated_at="2026-08-02")
    (row,) = doc["exercises"]
    assert row["hevy"] == "Goblet Squat"
    assert row["sessions"] == 5
    assert row["last_performed"] == "2026-07-01"
    assert row["hevy_equipment"] == "dumbbell"


def test_dump_is_valid_yaml_and_round_trips():
    doc = build_map_document(
        [_hevy("Goblet Squat", "dumbbell")], CATALOGUE, generated_at="2026-08-02"
    )
    text = dump_map(doc)
    assert yaml.safe_load(text) == doc


def test_dump_leads_with_review_instructions():
    text = dump_map(build_map_document([], CATALOGUE, generated_at="2026-08-02"))
    assert text.lstrip().startswith("#")
    assert "SKIP" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: FAIL, `ImportError: cannot import name 'build_map_document'`

- [ ] **Step 3: Write minimal implementation**

Add `import yaml` to the imports of `app/services/hevy_import.py`, then append:

```python
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
```

- [ ] **Step 4: Declare the PyYAML dependency**

`pyyaml` is already installed in the venv as a transitive dependency but is not declared. Add this line to `backend/requirements.txt`, keeping the file's existing ordering style:

```
pyyaml==6.0.3
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: PASS, 29 tests

- [ ] **Step 6: Commit**

```bash
git add app/services/hevy_import.py tests/test_hevy_import.py requirements.txt
git commit -m "[SH] feat: build reviewable Hevy mapping document"
```

---

### Task 5: Validate a reviewed mapping file

**Files:**
- Modify: `backend/app/services/hevy_import.py`
- Modify: `backend/tests/test_hevy_import.py`

**Interfaces:**
- Consumes: nothing from earlier tasks at runtime.
- Produces: `resolve_selection(raw: object, candidates: Sequence[str]) -> str | None` (returns the chosen exercise name, `"SKIP"`, or None when unresolved) and `validate_map(document: dict, known_exercises: set[str], known_patterns: set[str], known_equipment: set[str]) -> list[str]` returning human-readable error strings, empty when valid.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_hevy_import.py`:

```python
from app.services.hevy_import import resolve_selection, validate_map

KNOWN_EXERCISES = {"Dumbbell Goblet Squat", "Barbell Back Squat"}
KNOWN_PATTERNS = {"knee_dominant", "isolation", "conditioning"}
KNOWN_EQUIPMENT = {"Dumbbell", "Cable", "Rowing Machine"}


def _doc(*rows: dict) -> dict:
    return {"meta": {}, "exercises": list(rows)}


def test_index_selection_resolves_to_a_candidate_name():
    assert resolve_selection(2, ["First", "Second", "Third"]) == "Second"


def test_name_selection_passes_through():
    assert resolve_selection("Dumbbell Goblet Squat", []) == "Dumbbell Goblet Squat"


def test_skip_is_preserved():
    assert resolve_selection("SKIP", []) == "SKIP"


def test_null_selection_is_unresolved():
    assert resolve_selection(None, ["First"]) is None


def test_valid_document_has_no_errors():
    doc = _doc(
        {"hevy": "Goblet Squat", "slotfit": "Dumbbell Goblet Squat", "candidates": []},
        {"hevy": "Rest", "slotfit": "SKIP", "candidates": []},
        {
            "hevy": "Rowing Machine",
            "slotfit": None,
            "candidates": [],
            "create": {
                "name": "Rowing Machine",
                "pattern": "conditioning",
                "equipment": "Rowing Machine",
            },
        },
    )
    assert validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT) == []


def test_unresolved_entries_are_all_reported_at_once():
    doc = _doc(
        {"hevy": "A", "slotfit": None, "candidates": []},
        {"hevy": "B", "slotfit": None, "candidates": []},
    )
    errors = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert len(errors) == 2
    assert any("A" in e for e in errors) and any("B" in e for e in errors)


def test_unknown_exercise_name_is_an_error():
    doc = _doc({"hevy": "A", "slotfit": "No Such Exercise", "candidates": []})
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "No Such Exercise" in error


def test_unknown_pattern_slug_is_an_error():
    doc = _doc({
        "hevy": "A", "slotfit": None, "candidates": [],
        "create": {"name": "New Thing", "pattern": "not_a_pattern"},
    })
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "not_a_pattern" in error


def test_unknown_equipment_is_an_error():
    doc = _doc({
        "hevy": "A", "slotfit": None, "candidates": [],
        "create": {"name": "New Thing", "pattern": "isolation", "equipment": "Nope"},
    })
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "Nope" in error


def test_create_requires_a_pattern():
    doc = _doc({
        "hevy": "A", "slotfit": None, "candidates": [], "create": {"name": "New Thing"},
    })
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "pattern" in error


def test_setting_both_slotfit_and_create_is_an_error():
    doc = _doc({
        "hevy": "A", "slotfit": "Dumbbell Goblet Squat", "candidates": [],
        "create": {"name": "New Thing", "pattern": "isolation"},
    })
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "both" in error.lower()


def test_creating_an_existing_exercise_name_is_an_error():
    doc = _doc({
        "hevy": "A", "slotfit": None, "candidates": [],
        "create": {"name": "Barbell Back Squat", "pattern": "knee_dominant"},
    })
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "already exists" in error


def test_out_of_range_index_is_an_error():
    doc = _doc({"hevy": "A", "slotfit": 9, "candidates": ["Only One"]})
    (error,) = validate_map(doc, KNOWN_EXERCISES, KNOWN_PATTERNS, KNOWN_EQUIPMENT)
    assert "9" in error
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: FAIL, `ImportError: cannot import name 'resolve_selection'`

- [ ] **Step 3: Write minimal implementation**

Append to `app/services/hevy_import.py`:

```python
SKIP = "SKIP"


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
) -> list[str]:
    """Check a reviewed mapping document, returning every problem at once.

    Reporting all errors together matters: the reviewer resolves ~58 entries by
    hand, and fixing them one failed run at a time would be miserable.
    """
    errors: list[str] = []
    for row in document.get("exercises") or []:
        label = row.get("hevy", "<unnamed>")
        raw = row.get("slotfit")
        candidates = row.get("candidates") or []
        create = row.get("create")

        if create is not None and raw is not None:
            errors.append(
                f"{label}: sets both 'slotfit' and 'create' - choose one"
            )
            continue

        if create is not None:
            name = (create.get("name") or "").strip()
            pattern = create.get("pattern")
            equipment = create.get("equipment")
            if not name:
                errors.append(f"{label}: create needs a 'name'")
            elif name in known_exercises:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_import.py -v --no-cov`
Expected: PASS, 42 tests

- [ ] **Step 5: Commit**

```bash
git add app/services/hevy_import.py tests/test_hevy_import.py
git commit -m "[SH] feat: validate reviewed Hevy mapping files"
```

---

### Task 6: Apply the mapping to the database

**Files:**
- Modify: `backend/app/services/hevy_import.py`
- Create: `backend/tests/test_hevy_apply.py`

**Interfaces:**
- Consumes: `MACHINE_EQUIPMENT`, `resolve_selection`, `SKIP`.
- Produces: `ApplyResult` dataclass with int fields `equipment_created`, `exercises_created`, `staples_created`, `skipped_existing`, `skipped_no_pattern`, `skipped_explicit`; and `async def apply_map(db: AsyncSession, document: dict, user: User) -> ApplyResult`. The caller commits; `apply_map` only flushes.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_hevy_apply.py`:

```python
"""Tests for applying a reviewed Hevy mapping (app/services/hevy_import.apply_map)."""

import pytest
from sqlalchemy import select

from app.models import (
    User,
    Exercise,
    Equipment,
    MovementPattern,
    StapleExercise,
    ExercisePatternMap,
)
from app.services.pattern_taxonomy import (
    seed_movement_patterns,
    seed_exercise_pattern_map,
)
from app.services.hevy_import import MACHINE_EQUIPMENT, apply_map


async def _seed(test_db):
    """Seed patterns, one user, and one mappable exercise with a known pattern."""
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-0001")
    existing = Exercise(
        name="Cable V Grip Lat Pulldown",
        movement_pattern_1="Vertical Pull",
        mechanics="Compound",
    )
    test_db.add_all([user, existing])
    await test_db.flush()
    await seed_exercise_pattern_map(test_db)
    return user, existing


async def test_maps_an_existing_exercise_to_a_staple(test_db):
    user, existing = await _seed(test_db)
    doc = {"exercises": [
        {"hevy": "Lat Pulldown (Cable)", "slotfit": existing.name, "candidates": []},
    ]}

    result = await apply_map(test_db, doc, user)

    assert result.staples_created == 1
    staples = (await test_db.execute(select(StapleExercise))).scalars().all()
    assert len(staples) == 1
    assert staples[0].exercise_id == existing.id
    assert staples[0].user_id == user.id


async def test_skip_entries_write_nothing(test_db):
    user, _ = await _seed(test_db)
    doc = {"exercises": [{"hevy": "Rest", "slotfit": "SKIP", "candidates": []}]}

    result = await apply_map(test_db, doc, user)

    assert result.skipped_explicit == 1
    assert result.staples_created == 0
    assert (await test_db.execute(select(StapleExercise))).scalars().all() == []


async def test_creates_machine_equipment_rows(test_db):
    user, _ = await _seed(test_db)
    before = set((await test_db.execute(select(Equipment.name))).scalars().all())
    doc = {"exercises": [{
        "hevy": "Rowing Machine", "slotfit": None, "candidates": [],
        "create": {
            "name": "Rowing Machine",
            "pattern": "conditioning",
            "equipment": "Rowing Machine",
        },
    }]}

    result = await apply_map(test_db, doc, user)

    # Counted against what was already there, so the assertion holds whether or
    # not the test fixture seeds equipment.
    expected = len([n for n, _ in MACHINE_EQUIPMENT if n not in before])
    assert result.equipment_created == expected
    names = set(
        (await test_db.execute(select(Equipment.name))).scalars().all()
    )
    assert {"Rowing Machine", "Pec Deck", "Hyperextension Bench"} <= names
    categories = set(
        (await test_db.execute(select(Equipment.category))).scalars().all()
    )
    assert "Machine" in categories


async def test_created_exercise_is_custom_with_override_pattern(test_db):
    user, _ = await _seed(test_db)
    doc = {"exercises": [{
        "hevy": "Rowing Machine", "slotfit": None, "candidates": [],
        "create": {
            "name": "Rowing Machine",
            "pattern": "conditioning",
            "equipment": "Rowing Machine",
        },
    }]}

    result = await apply_map(test_db, doc, user)

    assert result.exercises_created == 1
    created = (
        await test_db.execute(select(Exercise).where(Exercise.name == "Rowing Machine"))
    ).scalar_one()
    assert created.is_custom == "True"
    assert created.primary_equipment_id is not None

    mapping = (
        await test_db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == created.id
            )
        )
    ).scalar_one()
    assert mapping.is_override is True
    pattern = (
        await test_db.execute(
            select(MovementPattern).where(MovementPattern.id == mapping.pattern_id)
        )
    ).scalar_one()
    assert pattern.slug == "conditioning"


async def test_seed_patterns_does_not_reclassify_created_customs(test_db):
    """The is_override flag must survive a routine seed_patterns run.

    Without it, seed_exercise_pattern_map rewrites the row and the hand-assigned
    conditioning pattern silently becomes isolation.
    """
    user, _ = await _seed(test_db)
    doc = {"exercises": [{
        "hevy": "Rowing Machine", "slotfit": None, "candidates": [],
        "create": {"name": "Rowing Machine", "pattern": "conditioning"},
    }]}
    await apply_map(test_db, doc, user)
    await test_db.commit()

    await seed_exercise_pattern_map(test_db)

    created = (
        await test_db.execute(select(Exercise).where(Exercise.name == "Rowing Machine"))
    ).scalar_one()
    mapping = (
        await test_db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == created.id
            )
        )
    ).scalar_one()
    pattern = (
        await test_db.execute(
            select(MovementPattern).where(MovementPattern.id == mapping.pattern_id)
        )
    ).scalar_one()
    assert pattern.slug == "conditioning"


async def test_apply_is_idempotent(test_db):
    user, existing = await _seed(test_db)
    doc = {"exercises": [
        {"hevy": "Lat Pulldown (Cable)", "slotfit": existing.name, "candidates": []},
        {"hevy": "Rowing Machine", "slotfit": None, "candidates": [],
         "create": {
             "name": "Rowing Machine",
             "pattern": "conditioning",
             "equipment": "Rowing Machine",
         }},
    ]}

    first = await apply_map(test_db, doc, user)
    await test_db.commit()
    second = await apply_map(test_db, doc, user)
    await test_db.commit()

    assert first.staples_created == 2
    assert second.staples_created == 0
    assert second.exercises_created == 0
    assert second.equipment_created == 0
    assert second.skipped_existing == 2

    equipment = (await test_db.execute(select(Equipment.name))).scalars().all()
    assert len(equipment) == len(set(equipment))
    staples = (await test_db.execute(select(StapleExercise))).scalars().all()
    assert len(staples) == 2


async def test_exercise_without_pattern_mapping_is_skipped(test_db):
    user, _ = await _seed(test_db)
    orphan = Exercise(name="Orphan Exercise")
    test_db.add(orphan)
    await test_db.flush()
    doc = {"exercises": [
        {"hevy": "Orphan", "slotfit": "Orphan Exercise", "candidates": []},
    ]}

    result = await apply_map(test_db, doc, user)

    assert result.skipped_no_pattern == 1
    assert result.staples_created == 0


async def test_index_selection_is_honoured(test_db):
    user, existing = await _seed(test_db)
    doc = {"exercises": [
        {"hevy": "Lat Pulldown", "slotfit": 1, "candidates": [existing.name]},
    ]}

    result = await apply_map(test_db, doc, user)

    assert result.staples_created == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_apply.py -v --no-cov`
Expected: FAIL, `ImportError: cannot import name 'apply_map'`

- [ ] **Step 3: Write minimal implementation**

Add these imports to `app/services/hevy_import.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Equipment,
    Exercise,
    ExercisePatternMap,
    MovementPattern,
    StapleExercise,
    User,
)
```

Then append:

```python
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
    existing = set(
        (await db.execute(select(Equipment.name))).scalars().all()
    )
    created = 0
    for name, category in MACHINE_EQUIPMENT:
        if name in existing:
            continue
        db.add(Equipment(name=name, category=category))
        created += 1
    if created:
        await db.flush()
    return created


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
        for eid, name in (
            await db.execute(select(Equipment.id, Equipment.name))
        ).all()
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
            name = create["name"].strip()
            exercise_id = exercise_ids.get(name)
            if exercise_id is None:
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
                exercise_ids[name] = exercise_id
                result.exercises_created += 1
                # is_override keeps seed_exercise_pattern_map from rewriting the
                # hand-assigned pattern on its next run.
                db.add(
                    ExercisePatternMap(
                        exercise_id=exercise_id,
                        pattern_id=pattern_ids[create["pattern"]],
                        is_override=True,
                    )
                )
                await db.flush()
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/Scripts/python.exe -m pytest tests/test_hevy_apply.py -v --no-cov`
Expected: PASS, 8 tests

- [ ] **Step 5: Run the whole suite to check for regressions**

Run: `./venv/Scripts/python.exe -m pytest -q`
Expected: PASS, 121 pre-existing tests plus the new ones

- [ ] **Step 6: Commit**

```bash
git add app/services/hevy_import.py tests/test_hevy_apply.py
git commit -m "[SH] feat: apply reviewed Hevy mapping to equipment, exercises, staples"
```

---

### Task 7: CLI script

**Files:**
- Create: `backend/scripts/hevy_staples.py`

**Interfaces:**
- Consumes: everything from Tasks 1-6.
- Produces: `python -m scripts.hevy_staples generate` and `python -m scripts.hevy_staples apply [--commit] [--device-id ID]`.

- [ ] **Step 1: Write the script**

```python
"""Seed a user's staple pool from a pulled Hevy history.

Two steps, with a human review in between:

    python -m scripts.hevy_staples generate       # writes hevy/exercise_map.yaml
    # ... edit the file, resolving every entry ...
    python -m scripts.hevy_staples apply          # dry run, prints the plan
    python -m scripts.hevy_staples apply --commit # writes

Run from backend/. Requires hevy/data/*.json from hevy/pull_hevy.py and a
database where scripts.seed_patterns has been run.
"""

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Equipment, Exercise, MovementPattern, User
from app.services.hevy_import import (
    MACHINE_EQUIPMENT,
    CatalogueEntry,
    apply_map,
    build_map_document,
    dump_map,
    select_exercises,
    validate_map,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "hevy" / "data"
MAP_PATH = REPO_ROOT / "hevy" / "exercise_map.yaml"


def _load_hevy_data() -> tuple[list[dict], dict[str, dict]]:
    workouts_path = DATA_DIR / "workouts.json"
    templates_path = DATA_DIR / "exercise_templates.json"
    if not workouts_path.is_file():
        raise SystemExit(
            f"error: {workouts_path} not found. Run: python hevy/pull_hevy.py"
        )
    workouts = json.loads(workouts_path.read_text(encoding="utf-8"))
    templates = {}
    if templates_path.is_file():
        templates = {
            t["id"]: t for t in json.loads(templates_path.read_text(encoding="utf-8"))
        }
    return workouts, templates


async def _resolve_user(db, device_id: str | None) -> User:
    if device_id:
        user = (
            await db.execute(select(User).where(User.device_id == device_id))
        ).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"error: no user with device_id {device_id!r}")
        return user
    users = (await db.execute(select(User))).scalars().all()
    if not users:
        raise SystemExit("error: no users in the database")
    if len(users) > 1:
        ids = ", ".join(u.device_id or f"id={u.id}" for u in users)
        raise SystemExit(f"error: several users exist, pass --device-id. Found: {ids}")
    print(f"Targeting the only user: {users[0].device_id}")
    return users[0]


async def generate(args: argparse.Namespace) -> int:
    workouts, templates = _load_hevy_data()
    exercises = select_exercises(
        workouts, templates, window_days=args.window_days, min_sessions=args.min_sessions
    )
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Exercise.name, Equipment.name).outerjoin(
                    Equipment, Exercise.primary_equipment_id == Equipment.id
                )
            )
        ).all()
    catalogue = [CatalogueEntry(name=n, equipment=e) for n, e in rows]

    document = build_map_document(
        exercises,
        catalogue,
        generated_at=date.today().isoformat(),
        window_days=args.window_days,
        min_sessions=args.min_sessions,
    )
    MAP_PATH.write_text(dump_map(document), encoding="utf-8")

    prefilled = sum(1 for r in document["exercises"] if r["slotfit"])
    total = len(document["exercises"])
    print(f"Wrote {MAP_PATH}")
    print(f"  {total} exercises, {prefilled} pre-filled, {total - prefilled} to review")
    return 0


async def apply(args: argparse.Namespace) -> int:
    if not MAP_PATH.is_file():
        raise SystemExit(
            f"error: {MAP_PATH} not found. Run: python -m scripts.hevy_staples generate"
        )
    document = yaml.safe_load(MAP_PATH.read_text(encoding="utf-8"))

    async with AsyncSessionLocal() as db:
        known_exercises = set(
            (await db.execute(select(Exercise.name))).scalars().all()
        )
        known_patterns = set(
            (await db.execute(select(MovementPattern.slug))).scalars().all()
        )
        if not known_patterns:
            raise SystemExit(
                "error: movement_patterns is empty. Run: python -m scripts.seed_patterns"
            )
        known_equipment = set(
            (await db.execute(select(Equipment.name))).scalars().all()
        ) | {name for name, _ in MACHINE_EQUIPMENT}

        errors = validate_map(
            document, known_exercises, known_patterns, known_equipment
        )
        if errors:
            print(f"{len(errors)} problem(s) in {MAP_PATH}:", file=sys.stderr)
            for error in errors:
                print(f"  {error}", file=sys.stderr)
            return 1

        user = await _resolve_user(db, args.device_id)
        result = await apply_map(db, document, user)

        print(f"  equipment created : {result.equipment_created}")
        print(f"  exercises created : {result.exercises_created}")
        print(f"  staples created   : {result.staples_created}")
        print(f"  already staple    : {result.skipped_existing}")
        print(f"  no pattern mapping: {result.skipped_no_pattern}")
        print(f"  skipped (SKIP)    : {result.skipped_explicit}")

        if args.commit:
            await db.commit()
            print("Committed.")
        else:
            await db.rollback()
            print("Dry run - nothing written. Re-run with --commit to apply.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="write the reviewable mapping file")
    gen.add_argument("--window-days", type=int, default=365)
    gen.add_argument("--min-sessions", type=int, default=3)
    gen.set_defaults(func=generate)

    app = sub.add_parser("apply", help="seed staples from the reviewed mapping file")
    app.add_argument("--commit", action="store_true", help="actually write")
    app.add_argument("--device-id", help="target user; optional when only one exists")
    app.set_defaults(func=apply)

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify generate runs against the real snapshot**

Run: `./venv/Scripts/python.exe -m scripts.hevy_staples generate`
Expected: writes `hevy/exercise_map.yaml`, prints `58 exercises, 1 pre-filled, 57 to review` (exact counts may shift if the Hevy data is re-pulled)

- [ ] **Step 3: Verify apply refuses an unreviewed file**

Run: `./venv/Scripts/python.exe -m scripts.hevy_staples apply`
Expected: exit 1, listing every unresolved entry, writing nothing

- [ ] **Step 4: Commit**

```bash
git add scripts/hevy_staples.py
git commit -m "[SH] feat: add hevy_staples generate/apply CLI"
```

---

### Task 8: Review the mapping and seed

This task is a human review, not code. It cannot be delegated to a subagent.

- [ ] **Step 1: Resolve every entry in `hevy/exercise_map.yaml`**

For each entry set `slotfit` to a candidate index, an exercise name, or `SKIP`; or add a `create` block with a `pattern` slug from: `horizontal_pull`, `horizontal_push`, `vertical_pull`, `vertical_push`, `knee_dominant`, `hip_hinge`, `core`, `carry`, `isolation`, `conditioning`.

- [ ] **Step 2: Dry-run**

Run: `./venv/Scripts/python.exe -m scripts.hevy_staples apply`
Expected: no validation errors, a printed plan, nothing written

- [ ] **Step 3: Apply**

Run: `./venv/Scripts/python.exe -m scripts.hevy_staples apply --commit`

- [ ] **Step 4: Verify idempotency against the real database**

Run: `./venv/Scripts/python.exe -m scripts.hevy_staples apply --commit`
Expected: all "created" counts are 0, `already staple` equals the first run's `staples created`

- [ ] **Step 5: Confirm pattern coverage**

Run: `./venv/Scripts/python.exe -c "import asyncio,sys; sys.path.insert(0,'.'); from sqlalchemy import select, func; from app.core.database import AsyncSessionLocal; from app.models import StapleExercise, MovementPattern;
async def m():
    async with AsyncSessionLocal() as db:
        rows=(await db.execute(select(MovementPattern.slug, func.count(StapleExercise.id)).outerjoin(StapleExercise, StapleExercise.pattern_id==MovementPattern.id).group_by(MovementPattern.slug).order_by(MovementPattern.slug))).all()
        [print(f'{s:18} {n}') for s,n in rows]
asyncio.run(m())"`
Expected: every pattern has at least one staple. A pattern showing 0 means partner suggestions for it will be empty — go back and map more exercises to it.

- [ ] **Step 6: Commit the reviewed mapping**

```bash
git add hevy/exercise_map.yaml
git commit -m "[SH] chore: add reviewed Hevy to SlotFit exercise mapping"
```
