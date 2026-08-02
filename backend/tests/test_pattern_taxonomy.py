"""Tests for movement pattern taxonomy"""
import pytest
from sqlalchemy import select

from app.models import MovementPattern, Exercise, ExercisePatternMap
from app.services.pattern_taxonomy import (
    seed_movement_patterns,
    classify_exercise,
    seed_exercise_pattern_map,
)


@pytest.mark.asyncio
async def test_seed_movement_patterns(test_db):
    await seed_movement_patterns(test_db)

    result = await test_db.execute(select(MovementPattern))
    patterns = {p.slug: p for p in result.scalars().all()}

    assert len(patterns) == 10
    assert patterns["horizontal_pull"].opposite_pattern_id == patterns["horizontal_push"].id
    assert patterns["horizontal_push"].opposite_pattern_id == patterns["horizontal_pull"].id
    assert patterns["vertical_pull"].opposite_pattern_id == patterns["vertical_push"].id
    assert patterns["knee_dominant"].opposite_pattern_id == patterns["hip_hinge"].id
    assert patterns["core"].is_neutral is True
    assert patterns["core"].opposite_pattern_id is None
    assert patterns["isolation"].is_neutral is True
    assert patterns["conditioning"].is_neutral is True
    assert patterns["carry"].is_neutral is True


@pytest.mark.asyncio
async def test_seed_is_idempotent(test_db):
    await seed_movement_patterns(test_db)
    await seed_movement_patterns(test_db)

    result = await test_db.execute(select(MovementPattern))
    assert len(result.scalars().all()) == 10


def test_classify_exercise_rollup():
    # Direct compound mappings
    assert classify_exercise("Horizontal Pull", "Compound") == "horizontal_pull"
    assert classify_exercise("Vertical Pull", "Compound") == "vertical_pull"
    assert classify_exercise("Horizontal Push", "Compound") == "horizontal_push"
    assert classify_exercise("Horizontal Adduction", "Compound") == "horizontal_push"
    assert classify_exercise("Vertical Push", "Compound") == "vertical_push"
    assert classify_exercise("Knee Dominant", "Compound") == "knee_dominant"
    assert classify_exercise("Hip Hinge", "Compound") == "hip_hinge"
    assert classify_exercise("Hip Extension", "Compound") == "hip_hinge"
    # Core wins even for compound mechanics
    assert classify_exercise("Anti-Extension", "Compound") == "core"
    assert classify_exercise("Rotational", "Compound") == "core"
    assert classify_exercise("Isometric Hold", "Compound") == "core"
    # Carry / conditioning
    assert classify_exercise("Loaded Carry", "Compound") == "carry"
    assert classify_exercise("Locomotion", "Compound") == "conditioning"
    # Isolation mechanics trumps direct map (leg extension is Knee Dominant + Isolation)
    assert classify_exercise("Knee Dominant", "Isolation") == "isolation"
    assert classify_exercise("Elbow Flexion", "Isolation") == "isolation"
    # Unknown / unsorted falls back to isolation
    assert classify_exercise("Unsorted*", "Compound") == "isolation"
    assert classify_exercise(None, None) == "isolation"


@pytest.mark.asyncio
async def test_seed_exercise_pattern_map(test_db):
    await seed_movement_patterns(test_db)
    test_db.add(Exercise(name="Cable Row", movement_pattern_1="Horizontal Pull", mechanics="Compound"))
    test_db.add(Exercise(name="Leg Extension", movement_pattern_1="Knee Dominant", mechanics="Isolation"))
    await test_db.commit()

    written = await seed_exercise_pattern_map(test_db)
    assert written == 2

    result = await test_db.execute(
        select(ExercisePatternMap, Exercise.name, MovementPattern.slug)
        .join(Exercise, Exercise.id == ExercisePatternMap.exercise_id)
        .join(MovementPattern, MovementPattern.id == ExercisePatternMap.pattern_id)
    )
    by_name = {name: slug for _, name, slug in result.all()}
    assert by_name["Cable Row"] == "horizontal_pull"
    assert by_name["Leg Extension"] == "isolation"


@pytest.mark.asyncio
async def test_seed_preserves_overrides(test_db):
    await seed_movement_patterns(test_db)
    ex = Exercise(name="Rowing Machine", movement_pattern_1="Horizontal Pull", mechanics="Compound")
    test_db.add(ex)
    await test_db.commit()
    await seed_exercise_pattern_map(test_db)

    # Manually override to conditioning
    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "conditioning"))
    conditioning = result.scalar_one()
    result = await test_db.execute(select(ExercisePatternMap).where(ExercisePatternMap.exercise_id == ex.id))
    row = result.scalar_one()
    row.pattern_id = conditioning.id
    row.is_override = True
    await test_db.commit()

    await seed_exercise_pattern_map(test_db)  # re-seed must not clobber
    await test_db.refresh(row)
    assert row.pattern_id == conditioning.id
