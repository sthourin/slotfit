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
