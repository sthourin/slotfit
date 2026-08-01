"""Tests for movement pattern taxonomy"""
import pytest
from sqlalchemy import select

from app.models import MovementPattern
from app.services.pattern_taxonomy import seed_movement_patterns


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
