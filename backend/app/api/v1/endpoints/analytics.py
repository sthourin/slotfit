"""
Analytics API endpoints
"""
from datetime import date, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.analytics_service import AnalyticsService
from app.models.user import User

router = APIRouter()


def get_current_week_monday() -> date:
    """Get the Monday of the current week (ISO week start)"""
    today = date.today()
    # weekday() returns 0 for Monday, 6 for Sunday
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)


@router.get("/weekly-volume", response_model=Dict[str, Any])
async def get_weekly_volume(
    week_start: Optional[date] = Query(None, description="Monday date of the week (ISO week start). Defaults to current week's Monday."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get weekly volume data for all muscle groups for a given week
    
    Returns volume metrics (sets, reps, total volume) per muscle group.
    If week_start is not provided, defaults to the current week's Monday.
    """
    # Default to current week's Monday if not provided
    if week_start is None:
        week_start = get_current_week_monday()
    
    # Validate that week_start is a Monday
    if week_start.weekday() != 0:
        raise HTTPException(
            status_code=400,
            detail="week_start must be a Monday (ISO week start)"
        )
    
    service = AnalyticsService(db)
    try:
        result = await service.get_weekly_volume(week_start, user_id=current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weekly volume: {str(e)}")


@router.get("/slot-performance", response_model=Dict[str, Any])
async def get_slot_performance(
    routine_id: int = Query(..., description="ID of the routine template"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance metrics for slots in a routine
    
    Returns completion rates, average sets, most used exercises per slot.
    """
    service = AnalyticsService(db)
    try:
        result = await service.get_slot_performance(routine_id, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get slot performance: {str(e)}")


@router.get("/exercise-progression/{exercise_id}", response_model=Dict[str, Any])
async def get_exercise_progression(
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get progression data for a specific exercise
    
    Returns personal records and recent workout history.
    """
    service = AnalyticsService(db)
    try:
        result = await service.get_exercise_progression(exercise_id, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get exercise progression: {str(e)}")
