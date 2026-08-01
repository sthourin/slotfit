"""Staple pool and exercise preference (blacklist) endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import StapleExercise, ExercisePreference, ExercisePatternMap, User
from app.schemas.staple import (
    StapleCreate,
    StapleResponse,
    PreferenceCreate,
    PreferenceResponse,
)
from app.services.history_service import last_performed_map

router = APIRouter()


class StaplePatch(BaseModel):
    """Request body for patching a staple (toggle is_active)"""

    is_active: bool


def _staple_response(staple: StapleExercise, last_performed=None) -> StapleResponse:
    """Convert a StapleExercise model to a response schema with optional last_performed date."""
    return StapleResponse(
        id=staple.id,
        pattern_id=staple.pattern_id,
        exercise_id=staple.exercise_id,
        exercise_name=staple.exercise.name,
        is_active=staple.is_active,
        added_at=staple.added_at,
        last_performed=last_performed,
    )


@router.get("/preferences", response_model=List[PreferenceResponse])
async def list_preferences(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """List exercise preferences (blacklist) for the current user."""
    result = await db.execute(
        select(ExercisePreference)
        .where(ExercisePreference.user_id == user.id)
        .options(selectinload(ExercisePreference.exercise))
    )
    return [
        PreferenceResponse(
            id=p.id,
            exercise_id=p.exercise_id,
            exercise_name=p.exercise.name,
            preference=p.preference,
        )
        for p in result.scalars().all()
    ]


@router.post("/preferences", response_model=PreferenceResponse, status_code=201)
async def create_preference(
    data: PreferenceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new exercise preference (blacklist entry) for the current user."""
    existing = (
        await db.execute(
            select(ExercisePreference).where(
                ExercisePreference.user_id == user.id,
                ExercisePreference.exercise_id == data.exercise_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Preference already exists")
    pref = ExercisePreference(
        user_id=user.id, exercise_id=data.exercise_id, preference=data.preference
    )
    db.add(pref)
    await db.commit()
    pref = (
        await db.execute(
            select(ExercisePreference)
            .where(ExercisePreference.id == pref.id)
            .options(selectinload(ExercisePreference.exercise))
        )
    ).scalar_one()
    return PreferenceResponse(
        id=pref.id,
        exercise_id=pref.exercise_id,
        exercise_name=pref.exercise.name,
        preference=pref.preference,
    )


@router.delete("/preferences/{pref_id}", status_code=204)
async def delete_preference(
    pref_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an exercise preference for the current user."""
    pref = (
        await db.execute(
            select(ExercisePreference).where(
                ExercisePreference.id == pref_id,
                ExercisePreference.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if pref is None:
        raise HTTPException(status_code=404, detail="Preference not found")
    await db.delete(pref)
    await db.commit()


@router.get("/", response_model=List[StapleResponse])
async def list_staples(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """List staple exercises for the current user, ordered by pattern and added date."""
    result = await db.execute(
        select(StapleExercise)
        .where(StapleExercise.user_id == user.id)
        .options(selectinload(StapleExercise.exercise))
        .order_by(StapleExercise.pattern_id, StapleExercise.added_at)
    )
    staples = result.scalars().all()
    last_map = await last_performed_map(db, user.id, [s.exercise_id for s in staples])
    return [_staple_response(s, last_map.get(s.exercise_id)) for s in staples]


@router.post("/", response_model=StapleResponse, status_code=201)
async def create_staple(
    data: StapleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new staple exercise for the current user.
    Resolves pattern_id from the exercise's pattern mapping on the server.
    """
    existing = (
        await db.execute(
            select(StapleExercise).where(
                StapleExercise.user_id == user.id,
                StapleExercise.exercise_id == data.exercise_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Exercise is already a staple")

    mapping = (
        await db.execute(
            select(ExercisePatternMap).where(
                ExercisePatternMap.exercise_id == data.exercise_id
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Exercise has no pattern mapping")

    staple = StapleExercise(
        user_id=user.id, pattern_id=mapping.pattern_id, exercise_id=data.exercise_id
    )
    db.add(staple)
    await db.commit()
    staple = (
        await db.execute(
            select(StapleExercise)
            .where(StapleExercise.id == staple.id)
            .options(selectinload(StapleExercise.exercise))
        )
    ).scalar_one()
    return _staple_response(staple)


@router.patch("/{staple_id}", response_model=StapleResponse)
async def patch_staple(
    staple_id: int,
    data: StaplePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update a staple exercise's is_active status for the current user.
    Only the owner of the staple may update it.
    """
    staple = (
        await db.execute(
            select(StapleExercise)
            .where(StapleExercise.id == staple_id, StapleExercise.user_id == user.id)
            .options(selectinload(StapleExercise.exercise))
        )
    ).scalar_one_or_none()
    if staple is None:
        raise HTTPException(status_code=404, detail="Staple not found")
    staple.is_active = data.is_active
    await db.commit()
    return _staple_response(staple)


@router.delete("/{staple_id}", status_code=204)
async def delete_staple(
    staple_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a staple exercise for the current user. Only the owner may delete it."""
    staple = (
        await db.execute(
            select(StapleExercise).where(
                StapleExercise.id == staple_id, StapleExercise.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if staple is None:
        raise HTTPException(status_code=404, detail="Staple not found")
    await db.delete(staple)
    await db.commit()
