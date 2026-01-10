"""
Injury API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.injury import InjuryType, UserInjury
from app.models.user import User
from app.schemas.injury import (
    InjuryTypeResponse,
    InjuryTypeListResponse,
    UserInjuryCreate,
    UserInjuryUpdate,
    UserInjuryResponse,
)

router = APIRouter()


@router.get("/injury-types", response_model=List[InjuryTypeListResponse])
async def list_injury_types(
    body_area: Optional[str] = Query(None, description="Filter by body area"),
    db: AsyncSession = Depends(get_db)
):
    """List all predefined injury types, optionally filtered by body area"""
    query = select(InjuryType)
    if body_area:
        query = query.where(InjuryType.body_area == body_area)
    query = query.order_by(InjuryType.body_area, InjuryType.name)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/injury-types/{injury_type_id}", response_model=InjuryTypeResponse)
async def get_injury_type(
    injury_type_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get injury type with its movement restrictions"""
    query = select(InjuryType).where(
        InjuryType.id == injury_type_id
    ).options(selectinload(InjuryType.restrictions))
    result = await db.execute(query)
    injury_type = result.scalar_one_or_none()
    if not injury_type:
        raise HTTPException(status_code=404, detail="Injury type not found")
    return injury_type


@router.get("/user-injuries", response_model=List[UserInjuryResponse])
async def list_user_injuries(
    active_only: bool = Query(True, description="Only return active injuries"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's injuries"""
    query = select(UserInjury).where(
        UserInjury.user_id == current_user.id
    ).options(
        selectinload(UserInjury.injury_type)
    )
    if active_only:
        query = query.where(UserInjury.is_active == True)
    query = query.order_by(UserInjury.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/user-injuries", response_model=UserInjuryResponse, status_code=201)
async def add_user_injury(
    injury: UserInjuryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add an injury to user's profile"""
    # Verify injury type exists
    injury_type = await db.get(InjuryType, injury.injury_type_id)
    if not injury_type:
        raise HTTPException(status_code=404, detail="Injury type not found")
    
    # Check for duplicate active injury for this user
    existing = await db.execute(
        select(UserInjury).where(
            UserInjury.injury_type_id == injury.injury_type_id,
            UserInjury.is_active == True,
            UserInjury.user_id == current_user.id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This injury is already in your profile")
    
    user_injury = UserInjury(**injury.model_dump(), user_id=current_user.id)
    db.add(user_injury)
    await db.commit()
    await db.refresh(user_injury)
    
    # Load relationship for response
    await db.refresh(user_injury, ["injury_type"])
    return user_injury


@router.put("/user-injuries/{injury_id}", response_model=UserInjuryResponse)
async def update_user_injury(
    injury_id: int,
    updates: UserInjuryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user injury (severity, notes, or mark as healed)"""
    query = select(UserInjury).where(
        UserInjury.id == injury_id,
        UserInjury.user_id == current_user.id
    )
    result = await db.execute(query)
    user_injury = result.scalar_one_or_none()
    
    if not user_injury:
        raise HTTPException(status_code=404, detail="User injury not found")
    
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(user_injury, field, value)
    
    await db.commit()
    await db.refresh(user_injury, ["injury_type"])
    return user_injury


@router.delete("/user-injuries/{injury_id}", status_code=204)
async def delete_user_injury(
    injury_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove injury from user's profile"""
    query = select(UserInjury).where(
        UserInjury.id == injury_id,
        UserInjury.user_id == current_user.id
    )
    result = await db.execute(query)
    user_injury = result.scalar_one_or_none()
    
    if not user_injury:
        raise HTTPException(status_code=404, detail="User injury not found")
    
    await db.delete(user_injury)
    await db.commit()
    return None
