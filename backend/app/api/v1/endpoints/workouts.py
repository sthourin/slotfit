"""
Workout Session API endpoints
"""
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import WorkoutSession, WorkoutExercise, WorkoutSet
from app.models.workout import WorkoutState
from app.schemas.workout import (
    WorkoutSessionCreate,
    WorkoutSessionUpdate,
    WorkoutSessionResponse,
    WorkoutSessionListResponse,
)

router = APIRouter()


@router.get("/", response_model=WorkoutSessionListResponse)
async def list_workouts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all workout sessions"""
    query = select(WorkoutSession).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    ).offset(skip).limit(limit).order_by(WorkoutSession.id.desc())
    
    result = await db.execute(query)
    workouts = result.scalars().unique().all()
    
    # Get total count
    count_query = select(func.count(WorkoutSession.id))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    return WorkoutSessionListResponse(
        workouts=[WorkoutSessionResponse.model_validate(w) for w in workouts],
        total=total,
    )


@router.get("/{workout_id}", response_model=WorkoutSessionResponse)
async def get_workout(
    workout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single workout session by ID"""
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout_id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    return WorkoutSessionResponse.model_validate(workout)


@router.post("/", response_model=WorkoutSessionResponse, status_code=201)
async def create_workout(
    workout_data: WorkoutSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workout session"""
    workout = WorkoutSession(
        routine_template_id=workout_data.routine_template_id,
        state=workout_data.state,
    )
    db.add(workout)
    await db.commit()
    await db.refresh(workout)
    
    # Reload with relationships
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout.id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    result = await db.execute(query)
    workout = result.scalar_one()
    
    return WorkoutSessionResponse.model_validate(workout)


@router.put("/{workout_id}", response_model=WorkoutSessionResponse)
async def update_workout(
    workout_id: int,
    workout_data: WorkoutSessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing workout session"""
    query = select(WorkoutSession).where(WorkoutSession.id == workout_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Update fields
    update_data = workout_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workout, field, value)
    
    await db.commit()
    await db.refresh(workout)
    
    # Reload with relationships
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout_id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    result = await db.execute(query)
    workout = result.scalar_one()
    
    return WorkoutSessionResponse.model_validate(workout)


@router.delete("/{workout_id}", status_code=204)
async def delete_workout(
    workout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a workout session"""
    query = select(WorkoutSession).where(WorkoutSession.id == workout_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    await db.delete(workout)
    await db.commit()
    
    return None


@router.post("/{workout_id}/start", response_model=WorkoutSessionResponse)
async def start_workout(
    workout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Start a workout session"""
    query = select(WorkoutSession).where(WorkoutSession.id == workout_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    if workout.state != WorkoutState.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start workout in state: {workout.state}"
        )
    
    workout.state = WorkoutState.ACTIVE
    workout.started_at = datetime.utcnow()
    workout.paused_at = None
    
    await db.commit()
    await db.refresh(workout)
    
    # Reload with relationships
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout_id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    result = await db.execute(query)
    workout = result.scalar_one()
    
    return WorkoutSessionResponse.model_validate(workout)


@router.post("/{workout_id}/pause", response_model=WorkoutSessionResponse)
async def pause_workout(
    workout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Pause a workout session"""
    query = select(WorkoutSession).where(WorkoutSession.id == workout_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    if workout.state != WorkoutState.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause workout in state: {workout.state}"
        )
    
    workout.state = WorkoutState.PAUSED
    workout.paused_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(workout)
    
    # Reload with relationships
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout_id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    result = await db.execute(query)
    workout = result.scalar_one()
    
    return WorkoutSessionResponse.model_validate(workout)


@router.post("/{workout_id}/complete", response_model=WorkoutSessionResponse)
async def complete_workout(
    workout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Complete a workout session"""
    query = select(WorkoutSession).where(WorkoutSession.id == workout_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    if workout.state not in [WorkoutState.ACTIVE, WorkoutState.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete workout in state: {workout.state}"
        )
    
    workout.state = WorkoutState.COMPLETED
    workout.completed_at = datetime.utcnow()
    workout.paused_at = None
    
    await db.commit()
    await db.refresh(workout)
    
    # Reload with relationships
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout_id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    result = await db.execute(query)
    workout = result.scalar_one()
    
    return WorkoutSessionResponse.model_validate(workout)


@router.post("/{workout_id}/abandon", response_model=WorkoutSessionResponse)
async def abandon_workout(
    workout_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Abandon a workout session"""
    query = select(WorkoutSession).where(WorkoutSession.id == workout_id)
    result = await db.execute(query)
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    workout.state = WorkoutState.ABANDONED
    workout.paused_at = None
    
    await db.commit()
    await db.refresh(workout)
    
    # Reload with relationships
    query = select(WorkoutSession).where(
        WorkoutSession.id == workout_id
    ).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.sets)
    )
    result = await db.execute(query)
    workout = result.scalar_one()
    
    return WorkoutSessionResponse.model_validate(workout)
