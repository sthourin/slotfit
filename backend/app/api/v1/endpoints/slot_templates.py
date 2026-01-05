"""
Slot Template API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import SlotTemplate
from app.models.slot_template import SlotType
from app.schemas.slot_template import (
    SlotTemplateCreate,
    SlotTemplateUpdate,
    SlotTemplateResponse,
)

router = APIRouter()


@router.get("/", response_model=List[SlotTemplateResponse])
async def list_slot_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    slot_type: Optional[SlotType] = Query(None, description="Filter by slot type"),
    db: AsyncSession = Depends(get_db),
):
    """List all slot templates, optionally filtered by slot_type"""
    query = select(SlotTemplate)
    
    # Apply slot_type filter if provided
    if slot_type:
        query = query.where(SlotTemplate.slot_type == slot_type)
    
    query = query.offset(skip).limit(limit).order_by(
        SlotTemplate.slot_type.asc(),
        SlotTemplate.name.asc()
    )
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [SlotTemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=SlotTemplateResponse)
async def get_slot_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single slot template by ID"""
    query = select(SlotTemplate).where(SlotTemplate.id == template_id)
    
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Slot template not found")
    
    return SlotTemplateResponse.model_validate(template)


@router.post("/", response_model=SlotTemplateResponse, status_code=201)
async def create_slot_template(
    template_data: SlotTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new slot template"""
    template = SlotTemplate(
        name=template_data.name,
        slot_type=template_data.slot_type,
        muscle_group_ids=template_data.muscle_group_ids,
        time_limit_seconds=template_data.time_limit_seconds,
        default_exercise_id=template_data.default_exercise_id,
        target_sets=template_data.target_sets,
        target_reps_min=template_data.target_reps_min,
        target_reps_max=template_data.target_reps_max,
        target_weight=template_data.target_weight,
        target_rest_seconds=template_data.target_rest_seconds,
        notes=template_data.notes,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    
    return SlotTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=SlotTemplateResponse)
async def update_slot_template(
    template_id: int,
    template_data: SlotTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a slot template"""
    query = select(SlotTemplate).where(SlotTemplate.id == template_id)
    
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Slot template not found")
    
    # Update fields
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    
    return SlotTemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=204)
async def delete_slot_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a slot template"""
    query = select(SlotTemplate).where(SlotTemplate.id == template_id)
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Slot template not found")
    
    await db.delete(template)
    await db.commit()
    
    return None
