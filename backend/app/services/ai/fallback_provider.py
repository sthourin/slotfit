"""
Fallback rule-based recommendation provider
Used when AI is unavailable
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.services.ai.base import AIProvider, RecommendationResponse, ExerciseRecommendation
from app.models import Exercise, MuscleGroup
from app.models.exercise import exercise_muscle_groups


class FallbackProvider(AIProvider):
    """Rule-based fallback when AI is unavailable"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def is_available(self) -> bool:
        """Fallback is always available"""
        return True
    
    async def get_exercise_recommendations(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations using rule-based logic
        """
        # Query exercises filtered by muscle groups and equipment
        query = select(Exercise).options(
            selectinload(Exercise.primary_equipment),
            selectinload(Exercise.secondary_equipment),
        )
        
        # Filter by muscle groups
        if muscle_group_ids:
            query = query.join(
                exercise_muscle_groups,
                Exercise.id == exercise_muscle_groups.c.exercise_id
            ).where(
                exercise_muscle_groups.c.muscle_group_id.in_(muscle_group_ids)
            ).distinct()
        
        # Filter by equipment (permissive: ANY equipment matches)
        if available_equipment_ids:
            query = query.where(
                or_(
                    Exercise.primary_equipment_id.in_(available_equipment_ids),
                    Exercise.secondary_equipment_id.in_(available_equipment_ids),
                )
            )
        
        # Execute query
        result = await self.db.execute(query)
        exercises = result.scalars().unique().all()
        
        total_candidates = len(exercises)
        filtered_by_equipment = total_candidates
        
        # Sort by recency (least recent first for variety)
        # If user history provided, use it; otherwise randomize
        if user_workout_history and "exercise_frequency" in user_workout_history:
            # Sort by frequency (least frequent first)
            exercise_freq = user_workout_history.get("exercise_frequency", {})
            exercises = sorted(
                exercises,
                key=lambda e: exercise_freq.get(e.id, 0),
            )
        else:
            # Random order if no history
            import random
            exercises = list(exercises)
            random.shuffle(exercises)
        
        # Create recommendations
        recommendations = []
        for i, exercise in enumerate(exercises[:limit]):
            # Calculate priority score (higher for less frequent exercises)
            if user_workout_history and "exercise_frequency" in user_workout_history:
                freq = user_workout_history["exercise_frequency"].get(exercise.id, 0)
                priority_score = max(0.0, 1.0 - (freq * 0.1))  # Lower frequency = higher priority
            else:
                priority_score = 1.0 - (i * 0.1)  # Decreasing priority
            
            # Get last performed date if available
            last_performed = None
            if user_workout_history and "last_performed" in user_workout_history:
                last_performed = user_workout_history["last_performed"].get(exercise.id)
            
            recommendations.append(
                ExerciseRecommendation(
                    exercise_id=exercise.id,
                    exercise_name=exercise.name,
                    priority_score=max(0.0, min(1.0, priority_score)),
                    reasoning=f"Rule-based recommendation based on muscle group targeting and equipment availability",
                    factors={
                        "frequency": "low" if not user_workout_history else "medium",
                        "last_performed": last_performed.isoformat() if last_performed else None,
                        "progression_opportunity": False,
                        "variety_boost": True,
                    },
                )
            )
        
        return RecommendationResponse(
            recommendations=recommendations,
            total_candidates=total_candidates,
            filtered_by_equipment=filtered_by_equipment,
            provider="fallback",
        )
