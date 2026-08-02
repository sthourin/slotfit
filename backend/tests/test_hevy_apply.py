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


async def test_creates_a_linked_variant_inheriting_the_base(test_db):
    """A HIIT variant is a separate exercise linked to its base, same pattern."""
    user, base = await _seed(test_db)
    doc = {"exercises": [{
        "hevy": "HIIT Lat Pulldowns", "slotfit": None, "candidates": [],
        "create": {
            "variant_of": base.name,
            "variant_type": "HIIT",
            "default_time_seconds": 40,
        },
    }]}

    result = await apply_map(test_db, doc, user)

    assert result.exercises_created == 1
    variant = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == f"{base.name} (HIIT)")
        )
    ).scalar_one()
    assert variant.base_exercise_id == base.id
    assert variant.variant_type == "HIIT"
    assert variant.default_time_seconds == 40
    assert variant.is_custom == "True"
    # Inherited from the base so pattern coverage and pairing still work.
    assert variant.primary_equipment_id == base.primary_equipment_id
    assert variant.movement_pattern_1 == base.movement_pattern_1

    base_map = (
        await test_db.execute(
            select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == base.id)
        )
    ).scalar_one()
    variant_map = (
        await test_db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == variant.id
            )
        )
    ).scalar_one()
    assert variant_map.pattern_id == base_map.pattern_id
    assert variant_map.is_override is True


async def test_variant_and_its_base_are_separate_staples(test_db):
    """The whole point: HIIT work must not merge into the strength staple."""
    user, base = await _seed(test_db)
    doc = {"exercises": [
        {"hevy": "Lat Pulldown (Cable)", "slotfit": base.name, "candidates": []},
        {"hevy": "HIIT Lat Pulldowns", "slotfit": None, "candidates": [],
         "create": {"variant_of": base.name, "variant_type": "HIIT"}},
    ]}

    result = await apply_map(test_db, doc, user)

    assert result.staples_created == 2
    staples = (await test_db.execute(select(StapleExercise))).scalars().all()
    assert len({s.exercise_id for s in staples}) == 2


async def test_variant_creation_is_idempotent(test_db):
    user, base = await _seed(test_db)
    doc = {"exercises": [{
        "hevy": "HIIT Lat Pulldowns", "slotfit": None, "candidates": [],
        "create": {"variant_of": base.name, "variant_type": "HIIT"},
    }]}

    await apply_map(test_db, doc, user)
    await test_db.commit()
    second = await apply_map(test_db, doc, user)

    assert second.exercises_created == 0
    assert second.staples_created == 0
    variants = (
        await test_db.execute(
            select(Exercise).where(Exercise.name == f"{base.name} (HIIT)")
        )
    ).scalars().all()
    assert len(variants) == 1
