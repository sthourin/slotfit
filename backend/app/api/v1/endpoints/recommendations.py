"""
AI Exercise Recommendation API endpoints
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.models.workout import WorkoutSession, WorkoutExercise, WorkoutState
from app.models.routine import RoutineTemplate, RoutineSlot
from app.models.exercise import Exercise
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
        await db.refresh(session, ["exercises"])
        for we in session.exercises:
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


async def get_training_summary(
    db: AsyncSession, user_id: int, planned_sessions: Optional[int] = None
) -> Dict[str, Any]:
    """
    Compute aggregated training summary for AI prompt context.
    Returns sets/reps per muscle group for 7d and 30d windows,
    plus days since each muscle group was last trained,
    and schedule variability info.
    """
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # Session counts per week (last 4 weeks) for variability calculation
    weekly_result = await db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE completed_at >= :w1) as week_1,
            COUNT(*) FILTER (WHERE completed_at >= :w2 AND completed_at < :w1) as week_2,
            COUNT(*) FILTER (WHERE completed_at >= :w3 AND completed_at < :w2) as week_3,
            COUNT(*) FILTER (WHERE completed_at >= :w4 AND completed_at < :w3) as week_4
        FROM workout_sessions
        WHERE user_id = :user_id
          AND completed_at IS NOT NULL
          AND completed_at >= :w4
    """), {
        "user_id": user_id,
        "w1": now - timedelta(days=7),
        "w2": now - timedelta(days=14),
        "w3": now - timedelta(days=21),
        "w4": now - timedelta(days=28),
    })
    weekly_row = weekly_result.fetchone()
    weekly_counts = [weekly_row[i] for i in range(4)] if weekly_row else [0, 0, 0, 0]
    sessions_7d = weekly_counts[0]
    sessions_30d = sum(weekly_counts)
    avg_per_week = round(sessions_30d / 4, 1)

    # Determine schedule pattern
    non_zero_weeks = [w for w in weekly_counts if w > 0]
    if len(non_zero_weeks) >= 2:
        spread = max(non_zero_weeks) - min(non_zero_weeks)
        schedule_pattern = "irregular" if spread >= 2 else "consistent"
    else:
        schedule_pattern = "irregular"

    # Volume by muscle group (sets + reps) for both 7d and 30d, with last_trained date
    volume_result = await db.execute(text("""
        SELECT
            mg.name as muscle_group,
            COUNT(ws.id) FILTER (WHERE wses.completed_at >= :seven_days) as sets_7d,
            COALESCE(SUM(ws.reps) FILTER (WHERE wses.completed_at >= :seven_days), 0) as reps_7d,
            COUNT(ws.id) as sets_30d,
            COALESCE(SUM(ws.reps), 0) as reps_30d,
            MAX(wses.completed_at) as last_trained
        FROM workout_sessions wses
        JOIN workout_exercises we ON we.workout_session_id = wses.id
        JOIN workout_sets ws ON ws.workout_exercise_id = we.id
        JOIN exercise_muscle_groups emg ON emg.exercise_id = we.exercise_id
        JOIN muscle_groups mg ON mg.id = emg.muscle_group_id
        WHERE wses.user_id = :user_id
          AND wses.completed_at IS NOT NULL
          AND wses.completed_at >= :thirty_days
          AND emg.role = 'target'
          AND mg.level = 1
        GROUP BY mg.name
        ORDER BY sets_30d DESC
    """), {"user_id": user_id, "seven_days": seven_days_ago, "thirty_days": thirty_days_ago})

    muscle_groups = []
    for row in volume_result.fetchall():
        days_since = (now - row.last_trained).days if row.last_trained else None
        muscle_groups.append({
            "name": row.muscle_group,
            "sets_7d": row.sets_7d,
            "reps_7d": int(row.reps_7d),
            "sets_30d": row.sets_30d,
            "reps_30d": int(row.reps_30d),
            "days_since_trained": days_since,
        })

    return {
        "sessions_7d": sessions_7d,
        "sessions_30d": sessions_30d,
        "avg_sessions_per_week": avg_per_week,
        "weekly_counts": weekly_counts,
        "schedule_pattern": schedule_pattern,
        "planned_sessions": planned_sessions,
        "muscle_groups": muscle_groups,
    }


@router.post("/next-workout", response_model=NextWorkoutSuggestionResponse)
async def get_next_workout_suggestion(
    planned_sessions: Optional[int] = Query(
        None, ge=1, le=7,
        description="How many sessions the user plans this week (1-7). If omitted, inferred from history.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-powered next workout suggestion based on user history and planned schedule"""
    service = AIRecommendationService(db)

    training_summary = await get_training_summary(db, current_user.id, planned_sessions)
    routine_options = await get_routine_options(db, current_user.id)

    # Get exercise names for AI prompt grounding (user's exercises + popular ones)
    user_ex_query = (
        select(Exercise.name)
        .join(WorkoutExercise, WorkoutExercise.exercise_id == Exercise.id)
        .join(WorkoutSession, WorkoutSession.id == WorkoutExercise.workout_session_id)
        .where(WorkoutSession.user_id == current_user.id)
        .distinct()
    )
    user_ex_result = await db.execute(user_ex_query)
    user_exercise_names = sorted({row[0] for row in user_ex_result.fetchall()})
    training_summary["available_exercise_names"] = user_exercise_names

    try:
        suggestion = await service.get_next_workout_suggestion(
            workout_history=training_summary,
            routine_options=routine_options,
        )
        return suggestion
    except Exception:
        logger.error("Error getting next workout suggestion", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get next workout suggestion")
