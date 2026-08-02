"""Tests for the Hevy import service (backend/app/services/hevy_import.py)."""

import pytest

from app.services.hevy_import import (
    MACHINE_EQUIPMENT,
    normalize_tokens,
    slotfit_equipment_for,
)


def test_normalize_unwraps_parentheticals():
    assert normalize_tokens("Incline Bench Press (Dumbbell)") == {
        "incline",
        "bench",
        "pres",
        "dumbbell",
    }


def test_normalize_folds_plurals_over_three_chars():
    # "triceps" and "tricep" must unify; short tokens are left alone
    assert normalize_tokens("Triceps") == normalize_tokens("Tricep")
    assert "abs" in normalize_tokens("Abs Crunch")


def test_normalize_strips_punctuation_and_stopwords():
    assert normalize_tokens("Seated Cable Row - V Grip (Cable)") == {
        "seated",
        "cable",
        "row",
        "v",
        "grip",
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
