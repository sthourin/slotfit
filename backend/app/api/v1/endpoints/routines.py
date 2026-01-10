"""
Routine Template API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import RoutineTemplate, RoutineSlot
from app.models.user import User
from app.schemas.routine import (
    RoutineTemplateCreate,
    RoutineTemplateUpdate,
    RoutineTemplateResponse,
    RoutineTemplateListResponse,
    RoutineSlotCreate,
)

router = APIRouter()


@router.get("/", response_model=RoutineTemplateListResponse)
async def list_routines(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all routine templates for the current user"""
    query = select(RoutineTemplate).where(
        RoutineTemplate.user_id == current_user.id
    ).options(
        selectinload(RoutineTemplate.slots)
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    routines = result.scalars().unique().all()
    
    # Get total count
    count_result = await db.execute(
        select(RoutineTemplate).where(RoutineTemplate.user_id == current_user.id)
    )
    total = len(count_result.scalars().all())
    
    return RoutineTemplateListResponse(
        routines=[RoutineTemplateResponse.model_validate(r) for r in routines],
        total=total,
    )


@router.get("/{routine_id}", response_model=RoutineTemplateResponse)
async def get_routine(
    routine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single routine template by ID (must belong to current user)"""
    query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id,
        RoutineTemplate.user_id == current_user.id
    ).options(selectinload(RoutineTemplate.slots))
    
    result = await db.execute(query)
    routine = result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    return RoutineTemplateResponse.model_validate(routine)


@router.post("/", response_model=RoutineTemplateResponse, status_code=201)
async def create_routine(
    routine_data: RoutineTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new routine template for the current user"""
    # Create routine
    routine = RoutineTemplate(
        name=routine_data.name,
        routine_type=routine_data.routine_type,
        workout_style=routine_data.workout_style,
        description=routine_data.description,
        user_id=current_user.id,
    )
    db.add(routine)
    await db.flush()
    
    # Create slots
    for slot_data in routine_data.slots:
        slot = RoutineSlot(
            routine_template_id=routine.id,
            name=slot_data.name,
            order=slot_data.order,
            muscle_group_ids=slot_data.muscle_group_ids,
            superset_tag=slot_data.superset_tag,
            selected_exercise_id=slot_data.selected_exercise_id,
            workout_style=slot_data.workout_style,
        )
        db.add(slot)
    
    await db.commit()
    await db.refresh(routine)
    
    # Reload with slots
    query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine.id
    ).options(selectinload(RoutineTemplate.slots))
    result = await db.execute(query)
    routine = result.scalar_one()
    
    return RoutineTemplateResponse.model_validate(routine)


@router.put("/{routine_id}", response_model=RoutineTemplateResponse)
async def update_routine(
    routine_id: int,
    routine_data: RoutineTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a routine template (must belong to current user)"""
    query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id,
        RoutineTemplate.user_id == current_user.id
    ).options(selectinload(RoutineTemplate.slots))
    
    result = await db.execute(query)
    routine = result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    # Update fields
    update_data = routine_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(routine, field, value)
    
    await db.commit()
    await db.refresh(routine)
    
    # Reload with slots
    result = await db.execute(query)
    routine = result.scalar_one()
    
    return RoutineTemplateResponse.model_validate(routine)


@router.delete("/{routine_id}", status_code=204)
async def delete_routine(
    routine_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a routine template (must belong to current user)"""
    query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id,
        RoutineTemplate.user_id == current_user.id
    )
    result = await db.execute(query)
    routine = result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    await db.delete(routine)
    await db.commit()
    
    return None


@router.post("/{routine_id}/slots", response_model=RoutineTemplateResponse, status_code=201)
async def add_slot(
    routine_id: int,
    slot_data: RoutineSlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a slot to a routine (must belong to current user)"""
    query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id,
        RoutineTemplate.user_id == current_user.id
    )
    result = await db.execute(query)
    routine = result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    # Get max order
    slots_query = select(RoutineSlot).where(
        RoutineSlot.routine_template_id == routine_id
    )
    slots_result = await db.execute(slots_query)
    existing_slots = slots_result.scalars().all()
    max_order = max([s.order for s in existing_slots], default=0)
    
    slot = RoutineSlot(
        routine_template_id=routine_id,
        name=slot_data.name,
        order=slot_data.order or max_order + 1,
        muscle_group_ids=slot_data.muscle_group_ids,
        superset_tag=slot_data.superset_tag,
        selected_exercise_id=slot_data.selected_exercise_id,
        workout_style=slot_data.workout_style,
    )
    db.add(slot)
    await db.commit()
    
    # Reload routine with slots
    query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id
    ).options(selectinload(RoutineTemplate.slots))
    result = await db.execute(query)
    routine = result.scalar_one()
    
    return RoutineTemplateResponse.model_validate(routine)


@router.put("/{routine_id}/slots/{slot_id}", response_model=RoutineTemplateResponse)
async def update_slot(
    routine_id: int,
    slot_id: int,
    slot_data: RoutineSlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a slot in a routine (must belong to current user)"""
    # Verify routine belongs to user
    routine_query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id,
        RoutineTemplate.user_id == current_user.id
    )
    routine_result = await db.execute(routine_query)
    routine = routine_result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    query = select(RoutineSlot).where(
        RoutineSlot.id == slot_id,
        RoutineSlot.routine_template_id == routine_id,
    )
    result = await db.execute(query)
    slot = result.scalar_one_or_none()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    # Update slot
    slot.name = slot_data.name
    slot.order = slot_data.order
    slot.muscle_group_ids = slot_data.muscle_group_ids
    slot.superset_tag = slot_data.superset_tag
    slot.selected_exercise_id = slot_data.selected_exercise_id
    slot.workout_style = slot_data.workout_style
    
    await db.commit()
    
    # Reload routine with slots
    routine_query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id
    ).options(selectinload(RoutineTemplate.slots))
    routine_result = await db.execute(routine_query)
    routine = routine_result.scalar_one()
    
    return RoutineTemplateResponse.model_validate(routine)


@router.delete("/{routine_id}/slots/{slot_id}", response_model=RoutineTemplateResponse)
async def delete_slot(
    routine_id: int,
    slot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a slot from a routine (must belong to current user)"""
    # Verify routine belongs to user
    routine_query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id,
        RoutineTemplate.user_id == current_user.id
    )
    routine_result = await db.execute(routine_query)
    routine = routine_result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    query = select(RoutineSlot).where(
        RoutineSlot.id == slot_id,
        RoutineSlot.routine_template_id == routine_id,
    )
    result = await db.execute(query)
    slot = result.scalar_one_or_none()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    await db.delete(slot)
    await db.commit()
    
    # Reload routine with slots
    routine_query = select(RoutineTemplate).where(
        RoutineTemplate.id == routine_id
    ).options(selectinload(RoutineTemplate.slots))
    routine_result = await db.execute(routine_query)
    routine = routine_result.scalar_one()
    
    return RoutineTemplateResponse.model_validate(routine)
