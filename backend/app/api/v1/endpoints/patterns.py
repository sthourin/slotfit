"""Movement pattern endpoints"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import MovementPattern, StapleExercise, User
from app.schemas.pattern import PatternResponse, PatternProgressResponse, TrendPoint
from app.services.progression_service import pattern_trend

router = APIRouter()


@router.get("/", response_model=List[PatternResponse])
async def list_patterns(db: AsyncSession = Depends(get_db)):
    """List the curated movement patterns."""
    result = await db.execute(
        select(MovementPattern).order_by(MovementPattern.display_order)
    )
    return [PatternResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/progress", response_model=List[PatternProgressResponse])
async def get_pattern_progress(
    weeks: int = Query(12, ge=1, le=52),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Normalized e1RM trend per pattern (only patterns where the user has staples)."""
    result = await db.execute(
        select(MovementPattern)
        .join(StapleExercise, StapleExercise.pattern_id == MovementPattern.id)
        .where(StapleExercise.user_id == user.id)
        .distinct()
        .order_by(MovementPattern.display_order)
    )
    responses = []
    for pattern in result.scalars().all():
        trend = await pattern_trend(db, user.id, pattern.id, weeks=weeks)
        responses.append(
            PatternProgressResponse(
                pattern_id=pattern.id,
                slug=pattern.slug,
                name=pattern.name,
                trend=[TrendPoint(**point) for point in trend],
            )
        )
    return responses
