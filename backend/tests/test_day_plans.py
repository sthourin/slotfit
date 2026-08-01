"""Tests for DayPlan models and API"""
import pytest
from sqlalchemy import select

from app.models import DayPlan, PatternGoal, MovementPattern, User
from app.services.pattern_taxonomy import seed_movement_patterns


@pytest.mark.asyncio
async def test_day_plan_with_goals(test_db):
    await seed_movement_patterns(test_db)
    user = User(device_id="test-device-12345")
    test_db.add(user)
    await test_db.flush()

    result = await test_db.execute(select(MovementPattern).where(MovementPattern.slug == "horizontal_pull"))
    hp = result.scalar_one()

    plan = DayPlan(
        user_id=user.id,
        name="Full Body A",
        warmup_preferences=[101, 102],
        rounds_target=3,
    )
    plan.goals.append(PatternGoal(pattern_id=hp.id, required=True, target_sets=6))
    test_db.add(plan)
    await test_db.commit()

    result = await test_db.execute(select(DayPlan).where(DayPlan.name == "Full Body A"))
    loaded = result.scalar_one()
    assert loaded.rounds_target == 3
    assert loaded.warmup_preferences == [101, 102]
    goals = (await test_db.execute(select(PatternGoal).where(PatternGoal.day_plan_id == loaded.id))).scalars().all()
    assert len(goals) == 1
    assert goals[0].required is True
    assert goals[0].rep_range_min is None  # defaults applied at service layer (8-12)
