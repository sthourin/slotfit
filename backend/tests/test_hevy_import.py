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
