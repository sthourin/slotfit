"""Tests for the bodyweight predicate."""
import pytest
from sqlalchemy import select

from app.models import Equipment, Exercise
from app.services.exercise_helpers import bodyweight_equipment_id, is_bodyweight


def test_null_equipment_is_treated_as_bodyweight():
    """No catalogue row has NULL today, but a hand-created exercise might."""
    assert is_bodyweight(Exercise(name="Handstand", primary_equipment_id=None))


def test_bodyweight_equipment_row_is_bodyweight():
    assert is_bodyweight(Exercise(name="Push Up", primary_equipment_id=2), bodyweight_id=2)


def test_loaded_exercise_is_not_bodyweight():
    assert not is_bodyweight(
        Exercise(name="Trap Bar Deadlift", primary_equipment_id=17), bodyweight_id=2
    )


def test_without_a_resolved_id_only_null_counts():
    """A database with no Bodyweight row must not guess that some id means bodyweight.

    Regression guard: a hardcoded id would classify whatever happened to own
    that id - "Dumbbell" in the test fixtures - as bodyweight.
    """
    assert not is_bodyweight(Exercise(name="Dumbbell Curl", primary_equipment_id=2))


@pytest.mark.asyncio
async def test_bodyweight_equipment_id_resolves_by_name(test_db):
    test_db.add_all([Equipment(name="Cable Machine"), Equipment(name="Bodyweight")])
    await test_db.flush()

    resolved = await bodyweight_equipment_id(test_db)
    bodyweight = (
        await test_db.execute(select(Equipment).where(Equipment.name == "Bodyweight"))
    ).scalar_one()
    assert resolved == bodyweight.id


@pytest.mark.asyncio
async def test_bodyweight_equipment_id_is_none_when_absent(test_db):
    test_db.add(Equipment(name="Cable Machine"))
    await test_db.flush()

    assert await bodyweight_equipment_id(test_db) is None
