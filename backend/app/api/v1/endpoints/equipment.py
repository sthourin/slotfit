"""
Equipment API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Equipment, Exercise
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
)

router = APIRouter()


@router.get("/", response_model=List[EquipmentResponse])
async def list_equipment(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all equipment"""
    query = select(Equipment).order_by(Equipment.name).offset(skip).limit(limit)
    result = await db.execute(query)
    equipment_list = result.scalars().all()
    
    # Count exercises using each equipment
    equipment_counts = {}
    
    # Count primary equipment usage
    primary_query = select(
        Exercise.primary_equipment_id,
        func.count(Exercise.id).label('count')
    ).where(
        Exercise.primary_equipment_id.isnot(None)
    ).group_by(Exercise.primary_equipment_id)
    
    primary_result = await db.execute(primary_query)
    for row in primary_result:
        equipment_counts[row.primary_equipment_id] = equipment_counts.get(row.primary_equipment_id, 0) + row.count
    
    # Count secondary equipment usage
    secondary_query = select(
        Exercise.secondary_equipment_id,
        func.count(Exercise.id).label('count')
    ).where(
        Exercise.secondary_equipment_id.isnot(None)
    ).group_by(Exercise.secondary_equipment_id)
    
    secondary_result = await db.execute(secondary_query)
    for row in secondary_result:
        equipment_counts[row.secondary_equipment_id] = equipment_counts.get(row.secondary_equipment_id, 0) + row.count
    
    # Build response with exercise counts
    response = []
    for eq in equipment_list:
        exercise_count = equipment_counts.get(eq.id, 0)
        response.append(EquipmentResponse(
            id=eq.id,
            name=eq.name,
            category=eq.category,
            exercise_count=exercise_count
        ))
    
    return response


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single equipment by ID"""
    query = select(Equipment).where(Equipment.id == equipment_id)
    result = await db.execute(query)
    equipment = result.scalar_one_or_none()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Count exercises using this equipment
    primary_count_query = select(func.count(Exercise.id)).where(
        Exercise.primary_equipment_id == equipment_id
    )
    secondary_count_query = select(func.count(Exercise.id)).where(
        Exercise.secondary_equipment_id == equipment_id
    )
    
    primary_result = await db.execute(primary_count_query)
    secondary_result = await db.execute(secondary_count_query)
    
    exercise_count = primary_result.scalar() + secondary_result.scalar()
    
    return EquipmentResponse(
        id=equipment.id,
        name=equipment.name,
        category=equipment.category,
        exercise_count=exercise_count
    )


@router.post("/", response_model=EquipmentResponse, status_code=201)
async def create_equipment(
    equipment_data: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new equipment"""
    # Check if equipment with same name already exists
    existing_query = select(Equipment).where(Equipment.name == equipment_data.name)
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Equipment with name '{equipment_data.name}' already exists"
        )
    
    # Create equipment
    equipment = Equipment(
        name=equipment_data.name,
        category=equipment_data.category,
    )
    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)
    
    return EquipmentResponse(
        id=equipment.id,
        name=equipment.name,
        category=equipment.category,
        exercise_count=0
    )


@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    equipment_data: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an equipment"""
    query = select(Equipment).where(Equipment.id == equipment_id)
    
    result = await db.execute(query)
    equipment = result.scalar_one_or_none()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Check if name is being changed and if new name already exists
    update_data = equipment_data.model_dump(exclude_unset=True)
    if "name" in update_data:
        name_check_query = select(Equipment).where(
            Equipment.name == update_data["name"],
            Equipment.id != equipment_id
        )
        name_check_result = await db.execute(name_check_query)
        if name_check_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Equipment with name '{update_data['name']}' already exists"
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(equipment, field, value)
    
    await db.commit()
    await db.refresh(equipment)
    
    # Count exercises using this equipment
    primary_count_query = select(func.count(Exercise.id)).where(
        Exercise.primary_equipment_id == equipment_id
    )
    secondary_count_query = select(func.count(Exercise.id)).where(
        Exercise.secondary_equipment_id == equipment_id
    )
    
    primary_result = await db.execute(primary_count_query)
    secondary_result = await db.execute(secondary_count_query)
    
    exercise_count = primary_result.scalar() + secondary_result.scalar()
    
    return EquipmentResponse(
        id=equipment.id,
        name=equipment.name,
        category=equipment.category,
        exercise_count=exercise_count
    )


@router.delete("/{equipment_id}", status_code=204)
async def delete_equipment(
    equipment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an equipment"""
    query = select(Equipment).where(Equipment.id == equipment_id)
    result = await db.execute(query)
    equipment = result.scalar_one_or_none()
    
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Check if equipment is being used by any exercises
    primary_count_query = select(func.count(Exercise.id)).where(
        Exercise.primary_equipment_id == equipment_id
    )
    secondary_count_query = select(func.count(Exercise.id)).where(
        Exercise.secondary_equipment_id == equipment_id
    )
    
    primary_result = await db.execute(primary_count_query)
    secondary_result = await db.execute(secondary_count_query)
    
    exercise_count = primary_result.scalar() + secondary_result.scalar()
    
    if exercise_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete equipment '{equipment.name}' because it is used by {exercise_count} exercise(s)"
        )
    
    await db.delete(equipment)
    await db.commit()
    
    return None
