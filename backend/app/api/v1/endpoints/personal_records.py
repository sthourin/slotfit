"""
Personal Records API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import PersonalRecord, Exercise
from app.models.personal_record import RecordType
from app.models.user import User
from app.schemas.personal_record import (
    PersonalRecordResponse,
    PersonalRecordListResponse,
    PersonalRecordCreate,
    PersonalRecordUpdate,
)

router = APIRouter()


@router.get("/", response_model=PersonalRecordListResponse)
async def list_personal_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    exercise_id: Optional[int] = Query(None, description="Filter by exercise ID"),
    record_type: Optional[RecordType] = Query(None, description="Filter by record type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all personal records for the current user, optionally filtered by exercise_id or record_type"""
    query = select(PersonalRecord).where(
        PersonalRecord.user_id == current_user.id
    ).options(
        selectinload(PersonalRecord.exercise)
    )
    
    # Apply filters
    if exercise_id:
        query = query.where(PersonalRecord.exercise_id == exercise_id)
    
    if record_type:
        query = query.where(PersonalRecord.record_type == record_type)
    
    # Order by most recent first
    query = query.order_by(desc(PersonalRecord.achieved_at))
    
    # Get total count before pagination
    count_query = select(func.count(PersonalRecord.id)).where(
        PersonalRecord.user_id == current_user.id
    )
    if exercise_id:
        count_query = count_query.where(PersonalRecord.exercise_id == exercise_id)
    if record_type:
        count_query = count_query.where(PersonalRecord.record_type == record_type)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return PersonalRecordListResponse(
        records=[PersonalRecordResponse.model_validate(r) for r in records],
        total=total
    )


@router.get("/exercise/{exercise_id}", response_model=PersonalRecordListResponse)
async def get_personal_records_for_exercise(
    exercise_id: int,
    record_type: Optional[RecordType] = Query(None, description="Filter by record type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all personal records for a specific exercise for the current user"""
    # Verify exercise exists
    exercise_query = select(Exercise).where(Exercise.id == exercise_id)
    exercise_result = await db.execute(exercise_query)
    exercise = exercise_result.scalar_one_or_none()
    
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Query personal records
    query = select(PersonalRecord).where(
        PersonalRecord.exercise_id == exercise_id,
        PersonalRecord.user_id == current_user.id
    ).options(
        selectinload(PersonalRecord.exercise)
    )
    
    if record_type:
        query = query.where(PersonalRecord.record_type == record_type)
    
    # Order by most recent first
    query = query.order_by(desc(PersonalRecord.achieved_at))
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return PersonalRecordListResponse(
        records=[PersonalRecordResponse.model_validate(r) for r in records],
        total=len(records)
    )


@router.post("/", response_model=PersonalRecordResponse, status_code=201)
async def create_personal_record(
    record_data: PersonalRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new personal record for the current user"""
    # Verify exercise exists
    exercise = await db.get(Exercise, record_data.exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Verify workout_session exists if provided
    if record_data.workout_session_id:
        from app.models import WorkoutSession
        workout = await db.get(WorkoutSession, record_data.workout_session_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout session not found")
        # Verify workout belongs to user
        if workout.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Workout session does not belong to user")
    
    # Create personal record
    personal_record = PersonalRecord(
        exercise_id=record_data.exercise_id,
        record_type=record_data.record_type,
        value=record_data.value,
        context=record_data.context,
        achieved_at=record_data.achieved_at,
        workout_session_id=record_data.workout_session_id,
        user_id=current_user.id,
    )
    db.add(personal_record)
    await db.commit()
    await db.refresh(personal_record)
    
    # Reload with relationships
    query = select(PersonalRecord).where(
        PersonalRecord.id == personal_record.id
    ).options(
        selectinload(PersonalRecord.exercise)
    )
    result = await db.execute(query)
    personal_record = result.scalar_one()
    
    return PersonalRecordResponse.model_validate(personal_record)


@router.get("/{record_id}", response_model=PersonalRecordResponse)
async def get_personal_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single personal record by ID (must belong to current user)"""
    query = select(PersonalRecord).where(
        PersonalRecord.id == record_id,
        PersonalRecord.user_id == current_user.id
    ).options(
        selectinload(PersonalRecord.exercise)
    )
    
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Personal record not found")
    
    return PersonalRecordResponse.model_validate(record)


@router.put("/{record_id}", response_model=PersonalRecordResponse)
async def update_personal_record(
    record_id: int,
    updates: PersonalRecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a personal record (must belong to current user)"""
    query = select(PersonalRecord).where(
        PersonalRecord.id == record_id,
        PersonalRecord.user_id == current_user.id
    )
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Personal record not found")
    
    # Validate exercise if being updated
    if updates.exercise_id is not None:
        exercise = await db.get(Exercise, updates.exercise_id)
        if not exercise:
            raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Validate workout_session if being updated
    if updates.workout_session_id is not None:
        from app.models import WorkoutSession
        workout = await db.get(WorkoutSession, updates.workout_session_id)
        if not workout:
            raise HTTPException(status_code=404, detail="Workout session not found")
        if workout.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Workout session does not belong to user")
    
    # Validate value if being updated
    if updates.value is not None and updates.value <= 0:
        raise HTTPException(status_code=400, detail="value must be greater than 0")
    
    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    
    await db.commit()
    await db.refresh(record)
    
    # Reload with relationships
    query = select(PersonalRecord).where(
        PersonalRecord.id == record_id
    ).options(
        selectinload(PersonalRecord.exercise)
    )
    result = await db.execute(query)
    record = result.scalar_one()
    
    return PersonalRecordResponse.model_validate(record)


@router.delete("/{record_id}", status_code=204)
async def delete_personal_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a personal record (must belong to current user)"""
    query = select(PersonalRecord).where(
        PersonalRecord.id == record_id,
        PersonalRecord.user_id == current_user.id
    )
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Personal record not found")
    
    await db.delete(record)
    await db.commit()
    
    return None
