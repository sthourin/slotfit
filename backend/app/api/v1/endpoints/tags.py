"""
Tag API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import Tag, Exercise, RoutineTemplate, WorkoutSession
from app.schemas.tag import Tag as TagSchema, TagCreate, TagListResponse

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=TagListResponse)
async def list_tags(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List tags with optional filtering
    """
    query = select(Tag)
    
    if search:
        query = query.where(Tag.name.ilike(f"%{search}%"))
    
    if category:
        query = query.where(Tag.category == category)
    
    # Get total count
    count_query = select(func.count()).select_from(Tag)
    if search:
        count_query = count_query.where(Tag.name.ilike(f"%{search}%"))
    if category:
        count_query = count_query.where(Tag.category == category)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination and ordering
    query = query.order_by(Tag.name).offset(skip).limit(limit)
    
    result = await db.execute(query)
    tags = result.scalars().all()
    
    return TagListResponse(
        tags=[TagSchema.model_validate(tag) for tag in tags],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=TagSchema, status_code=201)
async def create_tag(
    tag_data: TagCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new tag (or return existing if name matches)
    """
    # Check if tag with same name already exists
    existing = await db.execute(select(Tag).where(Tag.name == tag_data.name))
    existing_tag = existing.scalar_one_or_none()
    
    if existing_tag:
        return TagSchema.model_validate(existing_tag)
    
    # Create new tag
    tag = Tag(
        name=tag_data.name,
        category=tag_data.category,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    
    return TagSchema.model_validate(tag)


@router.get("/{tag_id}", response_model=TagSchema)
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a tag by ID
    """
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    return TagSchema.model_validate(tag)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a tag (cascade deletes all relationships)
    """
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    await db.delete(tag)
    await db.commit()
    
    return None


@router.post("/exercises/{exercise_id}/tags", response_model=TagSchema)
async def add_tag_to_exercise(
    exercise_id: int,
    tag_name: str = Query(..., description="Tag name (will be created if doesn't exist)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a tag to an exercise (creates tag if it doesn't exist)
    """
    # Get or create tag
    result = await db.execute(select(Tag).where(Tag.name == tag_name))
    tag = result.scalar_one_or_none()
    
    if not tag:
        tag = Tag(name=tag_name)
        db.add(tag)
        await db.flush()
    
    # Get exercise
    result = await db.execute(
        select(Exercise).where(Exercise.id == exercise_id).options(selectinload(Exercise.tags))
    )
    exercise = result.scalar_one_or_none()
    
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Add tag if not already present
    if tag not in exercise.tags:
        exercise.tags.append(tag)
        await db.commit()
    
    return TagSchema.model_validate(tag)


@router.delete("/exercises/{exercise_id}/tags/{tag_id}", status_code=204)
async def remove_tag_from_exercise(
    exercise_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a tag from an exercise
    """
    result = await db.execute(
        select(Exercise).where(Exercise.id == exercise_id).options(selectinload(Exercise.tags))
    )
    exercise = result.scalar_one_or_none()
    
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag in exercise.tags:
        exercise.tags.remove(tag)
        await db.commit()
    
    return None


@router.post("/routines/{routine_id}/tags", response_model=TagSchema)
async def add_tag_to_routine(
    routine_id: int,
    tag_name: str = Query(..., description="Tag name (will be created if doesn't exist)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a tag to a routine (creates tag if it doesn't exist)
    """
    # Get or create tag
    result = await db.execute(select(Tag).where(Tag.name == tag_name))
    tag = result.scalar_one_or_none()
    
    if not tag:
        tag = Tag(name=tag_name)
        db.add(tag)
        await db.flush()
    
    # Get routine
    result = await db.execute(
        select(RoutineTemplate).where(RoutineTemplate.id == routine_id).options(selectinload(RoutineTemplate.tags))
    )
    routine = result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    # Add tag if not already present
    if tag not in routine.tags:
        routine.tags.append(tag)
        await db.commit()
    
    return TagSchema.model_validate(tag)


@router.delete("/routines/{routine_id}/tags/{tag_id}", status_code=204)
async def remove_tag_from_routine(
    routine_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a tag from a routine
    """
    result = await db.execute(
        select(RoutineTemplate).where(RoutineTemplate.id == routine_id).options(selectinload(RoutineTemplate.tags))
    )
    routine = result.scalar_one_or_none()
    
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag in routine.tags:
        routine.tags.remove(tag)
        await db.commit()
    
    return None


@router.post("/workouts/{workout_id}/tags", response_model=TagSchema)
async def add_tag_to_workout(
    workout_id: int,
    tag_name: str = Query(..., description="Tag name (will be created if doesn't exist)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a tag to a workout (creates tag if it doesn't exist)
    """
    # Get or create tag
    result = await db.execute(select(Tag).where(Tag.name == tag_name))
    tag = result.scalar_one_or_none()
    
    if not tag:
        tag = Tag(name=tag_name)
        db.add(tag)
        await db.flush()
    
    # Get workout
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id).options(selectinload(WorkoutSession.tags))
    )
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    # Add tag if not already present
    if tag not in workout.tags:
        workout.tags.append(tag)
        await db.commit()
    
    return TagSchema.model_validate(tag)


@router.delete("/workouts/{workout_id}/tags/{tag_id}", status_code=204)
async def remove_tag_from_workout(
    workout_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a tag from a workout
    """
    result = await db.execute(
        select(WorkoutSession).where(WorkoutSession.id == workout_id).options(selectinload(WorkoutSession.tags))
    )
    workout = result.scalar_one_or_none()
    
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag in workout.tags:
        workout.tags.remove(tag)
        await db.commit()
    
    return None
