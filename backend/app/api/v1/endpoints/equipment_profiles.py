"""
Equipment Profile API endpoints
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import EquipmentProfile
from app.models.user import User
from app.schemas.equipment_profile import (
    EquipmentProfileCreate,
    EquipmentProfileUpdate,
    EquipmentProfileResponse,
)

router = APIRouter()


@router.get("/", response_model=List[EquipmentProfileResponse])
async def list_equipment_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all equipment profiles for the current user"""
    query = select(EquipmentProfile).where(
        EquipmentProfile.user_id == current_user.id
    ).offset(skip).limit(limit).order_by(
        EquipmentProfile.is_default.desc(),  # Default profiles first
        EquipmentProfile.name.asc()
    )
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    return [EquipmentProfileResponse.model_validate(p) for p in profiles]


@router.get("/{profile_id}", response_model=EquipmentProfileResponse)
async def get_equipment_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single equipment profile by ID (must belong to current user)"""
    query = select(EquipmentProfile).where(
        EquipmentProfile.id == profile_id,
        EquipmentProfile.user_id == current_user.id
    )
    
    result = await db.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    
    return EquipmentProfileResponse.model_validate(profile)


@router.post("/", response_model=EquipmentProfileResponse, status_code=201)
async def create_equipment_profile(
    profile_data: EquipmentProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new equipment profile for the current user"""
    # If this is being set as default, clear other defaults first for this user
    if profile_data.is_default:
        await db.execute(
            update(EquipmentProfile)
            .where(
                EquipmentProfile.is_default == True,
                EquipmentProfile.user_id == current_user.id
            )
            .values(is_default=False)
        )
        await db.flush()
    
    # Create profile
    profile = EquipmentProfile(
        name=profile_data.name,
        equipment_ids=profile_data.equipment_ids,
        is_default=profile_data.is_default or False,
        user_id=current_user.id,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    
    return EquipmentProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=EquipmentProfileResponse)
async def update_equipment_profile(
    profile_id: int,
    profile_data: EquipmentProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an equipment profile (must belong to current user)"""
    query = select(EquipmentProfile).where(
        EquipmentProfile.id == profile_id,
        EquipmentProfile.user_id == current_user.id
    )
    
    result = await db.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    
    # If setting as default, clear other defaults first for this user
    update_data = profile_data.model_dump(exclude_unset=True)
    if update_data.get("is_default") is True:
        await db.execute(
            update(EquipmentProfile)
            .where(
                EquipmentProfile.is_default == True,
                EquipmentProfile.id != profile_id,
                EquipmentProfile.user_id == current_user.id
            )
            .values(is_default=False)
        )
        await db.flush()
    
    # Update fields
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    return EquipmentProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_equipment_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an equipment profile (must belong to current user)"""
    query = select(EquipmentProfile).where(
        EquipmentProfile.id == profile_id,
        EquipmentProfile.user_id == current_user.id
    )
    result = await db.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    
    await db.delete(profile)
    await db.commit()
    
    return None


@router.post("/{profile_id}/set-default", response_model=EquipmentProfileResponse)
async def set_default_equipment_profile(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set an equipment profile as the default (clears other defaults for this user)"""
    query = select(EquipmentProfile).where(
        EquipmentProfile.id == profile_id,
        EquipmentProfile.user_id == current_user.id
    )
    result = await db.execute(query)
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Equipment profile not found")
    
    # Clear is_default on all other profiles for this user
    await db.execute(
        update(EquipmentProfile)
        .where(
            EquipmentProfile.id != profile_id,
            EquipmentProfile.user_id == current_user.id
        )
        .values(is_default=False)
    )
    
    # Set this profile as default
    profile.is_default = True
    await db.commit()
    await db.refresh(profile)
    
    return EquipmentProfileResponse.model_validate(profile)
