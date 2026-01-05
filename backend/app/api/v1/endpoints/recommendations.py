"""
AI Exercise Recommendation API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ai.service import AIRecommendationService
from app.services.ai.base import RecommendationResponse

router = APIRouter()


@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    muscle_group_ids: List[int] = Query(..., description="List of muscle group IDs for slot scope"),
    available_equipment_ids: List[int] = Query(..., description="List of available equipment IDs"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    use_cache: bool = Query(True, description="Use cached recommendations if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered exercise recommendations for a slot
    
    Returns top exercises prioritized based on:
    - Muscle group targeting
    - Equipment availability
    - User workout history (if available)
    - Workout variety
    """
    if not muscle_group_ids:
        raise HTTPException(status_code=400, detail="muscle_group_ids cannot be empty")
    
    service = AIRecommendationService(db)
    
    # TODO: Get user workout history from database
    # For now, pass None (MVP is offline-only)
    user_workout_history = None
    
    try:
        response = await service.get_recommendations(
            muscle_group_ids=muscle_group_ids,
            available_equipment_ids=available_equipment_ids,
            user_workout_history=user_workout_history,
            limit=limit,
            use_cache=use_cache,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")
