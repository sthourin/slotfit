"""Day plan endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import DayPlan, PatternGoal, User
from app.schemas.day_plan import DayPlanCreate, DayPlanUpdate, DayPlanResponse

router = APIRouter()


async def _get_owned_plan(db: AsyncSession, user: User, plan_id: int) -> DayPlan:
    """Fetch a day plan if owned by the given user, else raise 404."""
    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.id == plan_id, DayPlan.user_id == user.id)
        .options(selectinload(DayPlan.goals))
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Day plan not found")
    return plan


@router.get("/", response_model=List[DayPlanResponse])
async def list_day_plans(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """List all day plans for the current user, ordered by name."""
    result = await db.execute(
        select(DayPlan)
        .where(DayPlan.user_id == user.id)
        .options(selectinload(DayPlan.goals))
        .order_by(DayPlan.name)
    )
    return [DayPlanResponse.model_validate(p) for p in result.scalars().all()]


@router.post("/", response_model=DayPlanResponse, status_code=201)
async def create_day_plan(
    data: DayPlanCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new day plan with goals for the current user."""
    plan = DayPlan(
        user_id=user.id,
        name=data.name,
        description=data.description,
        warmup_preferences=data.warmup_preferences,
        rounds_target=data.rounds_target,
    )
    for goal in data.goals:
        plan.goals.append(PatternGoal(**goal.model_dump()))
    db.add(plan)
    await db.commit()
    return DayPlanResponse.model_validate(await _get_owned_plan(db, user, plan.id))


@router.get("/{plan_id}", response_model=DayPlanResponse)
async def get_day_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve a day plan by ID if owned by the current user."""
    return DayPlanResponse.model_validate(await _get_owned_plan(db, user, plan_id))


@router.put("/{plan_id}", response_model=DayPlanResponse)
async def update_day_plan(
    plan_id: int,
    data: DayPlanUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update a day plan; goals list replaces all when provided."""
    plan = await _get_owned_plan(db, user, plan_id)
    for field in ("name", "description", "warmup_preferences", "rounds_target"):
        value = getattr(data, field)
        if value is not None:
            setattr(plan, field, value)
    if data.goals is not None:
        plan.goals.clear()
        for goal in data.goals:
            plan.goals.append(PatternGoal(**goal.model_dump()))
    await db.commit()
    return DayPlanResponse.model_validate(await _get_owned_plan(db, user, plan_id))


@router.delete("/{plan_id}", status_code=204)
async def delete_day_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a day plan if owned by the current user."""
    plan = await _get_owned_plan(db, user, plan_id)
    await db.delete(plan)
    await db.commit()
