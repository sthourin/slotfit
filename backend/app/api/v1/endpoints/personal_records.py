"""
Personal Records API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import PersonalRecord, Exercise
from app.models.personal_record import RecordType
from app.schemas.personal_record import (
    PersonalRecordResponse,
    PersonalRecordListResponse,
)

router = APIRouter()


@router.get("/", response_model=PersonalRecordListResponse)
async def list_personal_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    exercise_id: Optional[int] = Query(None, description="Filter by exercise ID"),
    record_type: Optional[RecordType] = Query(None, description="Filter by record type"),
    db: AsyncSession = Depends(get_db),
):
    """List all personal records, optionally filtered by exercise_id or record_type"""
    query = select(PersonalRecord).options(
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
    count_query = select(func.count(PersonalRecord.id))
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
    db: AsyncSession = Depends(get_db),
):
    """Get all personal records for a specific exercise"""
    # Verify exercise exists
    exercise_query = select(Exercise).where(Exercise.id == exercise_id)
    exercise_result = await db.execute(exercise_query)
    exercise = exercise_result.scalar_one_or_none()
    
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Query personal records
    query = select(PersonalRecord).where(
        PersonalRecord.exercise_id == exercise_id
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
