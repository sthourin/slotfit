"""Bodyweight readings endpoints"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import BodyweightReading, User
from app.schemas.bodyweight_reading import (
    BodyweightReadingCreate,
    BodyweightReadingResponse,
)

router = APIRouter()


@router.get("", response_model=List[BodyweightReadingResponse])
async def list_readings(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """A user's bodyweight readings, newest first."""
    result = await db.execute(
        select(BodyweightReading)
        .where(BodyweightReading.user_id == user.id)
        .order_by(BodyweightReading.recorded_at.desc())
    )
    return result.scalars().all()


@router.post(
    "", response_model=BodyweightReadingResponse, status_code=status.HTTP_201_CREATED
)
async def create_reading(
    data: BodyweightReadingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record a bodyweight reading.

    Upserts on (user, instant, source) so re-syncing the same measurement
    updates it in place instead of failing on the unique constraint. Manual
    entry and a synced reading at the same instant stay independent.
    """
    recorded_at = data.recorded_at or datetime.utcnow()
    existing = (
        await db.execute(
            select(BodyweightReading).where(
                BodyweightReading.user_id == user.id,
                BodyweightReading.recorded_at == recorded_at,
                BodyweightReading.source == data.source,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.weight = data.weight
        await db.commit()
        await db.refresh(existing)
        return existing

    reading = BodyweightReading(
        user_id=user.id,
        weight=data.weight,
        recorded_at=recorded_at,
        source=data.source,
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading(
    reading_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a reading. Scoped to the caller's own rows."""
    reading = (
        await db.execute(
            select(BodyweightReading).where(
                BodyweightReading.id == reading_id,
                BodyweightReading.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if reading is not None:
        await db.delete(reading)
        await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
