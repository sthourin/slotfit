"""
AI Exercise Recommendation API endpoints
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.models.workout import WorkoutSession, WorkoutExercise, WorkoutState
from app.models.routine import RoutineTemplate, RoutineSlot
from app.services.ai.service import AIRecommendationService
from app.services.ai.base import RecommendationResponse
from app.schemas.recommendation import NextWorkoutSuggestionResponse

router = APIRouter()
logger = get_logger(__name__)


async def get_user_workout_history(
    db: AsyncSession,
    user_id: int,
    days_back: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Get user's workout history for recommendation context.
    
    Returns a dictionary with:
    - recent_exercises: List of exercises performed in last N days
    - exercise_frequency: Dict mapping exercise_id to count
    - last_performed: Dict mapping exercise_id to last performed date
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Query recent workout sessions
    sessions_query = select(WorkoutSession).where(
        WorkoutSession.user_id == user_id,
        WorkoutSession.completed_at.isnot(None),
        WorkoutSession.completed_at >= cutoff_date
    ).order_by(WorkoutSession.completed_at.desc())
    
    result = await db.execute(sessions_query)
    sessions = result.scalars().all()
    
    if not sessions:
        return None
    
    # Extract exercise data
    recent_exercises = []
    exercise_frequency = {}
    last_performed = {}
    
    for session in sessions:
        # Load workout exercises with exercise relationship
        await db.refresh(session, ["workout_exercises"])
        for we in session.workout_exercises:
            exercise_id = we.exercise_id
            if exercise_id:
                recent_exercises.append(exercise_id)
                exercise_frequency[exercise_id] = exercise_frequency.get(exercise_id, 0) + 1
                if exercise_id not in last_performed:
                    last_performed[exercise_id] = session.completed_at
    
    return {
        "recent_exercises": recent_exercises,
        "exercise_frequency": exercise_frequency,
        "last_performed": last_performed,
        "total_sessions": len(sessions),
    }


async def get_recent_completed_workouts(
    db: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[WorkoutSession]:
    """Get recent completed workouts for a user"""
    query = select(WorkoutSession).where(
        WorkoutSession.user_id == user_id,
        WorkoutSession.state == WorkoutState.COMPLETED,
    ).order_by(WorkoutSession.completed_at.desc()).limit(limit).options(
        selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise),
    )
    result = await db.execute(query)
    return result.scalars().unique().all()


async def get_routine_options(
    db: AsyncSession,
    user_id: int,
) -> List[Dict[str, Any]]:
    """Get routine options for AI suggestion context"""
    query = select(RoutineTemplate).where(
        RoutineTemplate.user_id == user_id
    ).options(
        selectinload(RoutineTemplate.slots),
        selectinload(RoutineTemplate.tags),
    )
    result = await db.execute(query)
    routines = result.scalars().unique().all()

    routine_options = []
    for routine in routines:
        muscle_group_ids: List[int] = []
        for slot in routine.slots:
            if slot.muscle_group_ids:
                muscle_group_ids.extend(slot.muscle_group_ids)
        routine_options.append({
            "id": routine.id,
            "name": routine.name,
            "routine_type": routine.routine_type,
            "workout_style": routine.workout_style,
            "description": routine.description,
            "tag_names": [tag.name for tag in routine.tags],
            "slot_count": len(routine.slots),
            "muscle_group_ids": list(sorted(set(muscle_group_ids))),
        })
    return routine_options


@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    muscle_group_ids: List[int] = Query(..., description="List of muscle group IDs for slot scope"),
    available_equipment_ids: List[int] = Query(default=[], description="List of available equipment IDs"),
    workout_session_id: Optional[int] = Query(None, description="Optional workout session ID to calculate movement pattern balance"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    use_cache: bool = Query(True, description="Use cached recommendations if available"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AI-powered exercise recommendations for a slot
    
    Returns top exercises prioritized based on:
    - Muscle group targeting
    - Equipment availability
    - User workout history (recent exercises, frequency)
    - User injuries (filtered out)
    - Workout variety
    - Movement pattern balance (push/pull, compound/isolation)
    """
    if not muscle_group_ids:
        raise HTTPException(status_code=400, detail="muscle_group_ids cannot be empty")
    
    service = AIRecommendationService(db)
    
    # Get user workout history
    user_workout_history = await get_user_workout_history(db, current_user.id)
    
    if user_workout_history:
        logger.debug(
            f"Using workout history for user {current_user.id}: {user_workout_history['total_sessions']} sessions"
        )
    
    try:
        response = await service.get_recommendations(
            muscle_group_ids=muscle_group_ids,
            available_equipment_ids=available_equipment_ids,
            user_workout_history=user_workout_history,
            workout_session_id=workout_session_id,
            limit=limit,
            use_cache=use_cache,
            user_id=current_user.id,  # Pass user_id for injury filtering
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting recommendations",
            exc_info=True,
            extra={
                "user_id": current_user.id,
                "muscle_group_ids": muscle_group_ids,
            }
        )
        raise HTTPException(status_code=500, detail="Failed to get recommendations")


@router.post("/next-workout", response_model=NextWorkoutSuggestionResponse)
async def get_next_workout_suggestion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-powered next workout suggestion based on user history"""
    service = AIRecommendationService(db)

    user_workout_history = await get_user_workout_history(db, current_user.id)
    recent_workouts = await get_recent_completed_workouts(db, current_user.id, limit=10)
    routine_options = await get_routine_options(db, current_user.id)

    # Build summary for AI prompt
    routine_usage: Dict[int, int] = {}
    last_completed_by_routine: Dict[int, Any] = {}
    recent_sessions: List[Dict[str, Any]] = []

    for session in recent_workouts:
        if session.routine_template_id:
            routine_usage[session.routine_template_id] = routine_usage.get(session.routine_template_id, 0) + 1
            if session.routine_template_id not in last_completed_by_routine:
                last_completed_by_routine[session.routine_template_id] = session.completed_at
        recent_sessions.append({
            "id": session.id,
            "routine_template_id": session.routine_template_id,
            "completed_at": session.completed_at,
        })

    workout_history = {
        "recent_sessions": recent_sessions,
        "routine_usage": routine_usage,
        "last_completed_by_routine": last_completed_by_routine,
        "exercise_history": user_workout_history or {},
    }

    try:
        suggestion = await service.get_next_workout_suggestion(
            workout_history=workout_history,
            routine_options=routine_options,
        )
        return suggestion
    except Exception:
        logger.error("Error getting next workout suggestion", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get next workout suggestion")
