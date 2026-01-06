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
        weekly_volume: Optional[Dict[int, Dict[str, Any]]] = None,
        movement_patterns: Optional[Dict[str, Dict[str, int]]] = None,
        limit: int = 5,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations using rule-based logic
        """
        # Query exercises filtered by muscle groups and equipment
        query = select(Exercise).options(
            selectinload(Exercise.primary_equipment),
            selectinload(Exercise.secondary_equipment),
            selectinload(Exercise.muscle_groups),
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
        
        # Helper function to get weekly volume status for an exercise
        def get_weekly_volume_status(exercise: Exercise) -> str:
            """Determine weekly volume status based on exercise's muscle groups"""
            if not weekly_volume or not exercise.muscle_groups:
                return "low"
            
            # Get the maximum sets for any muscle group this exercise targets
            max_sets = 0
            for mg in exercise.muscle_groups:
                if mg.id in weekly_volume:
                    sets = weekly_volume[mg.id].get('total_sets', 0)
                    max_sets = max(max_sets, sets)
            
            if max_sets > 20:
                return "high"
            elif max_sets > 10:
                return "moderate"
            else:
                return "low"
        
        # Helper function to calculate volume penalty for sorting
        def get_volume_penalty(exercise: Exercise) -> float:
            """Return penalty score (0.0-1.0) based on weekly volume - higher penalty for high volume"""
            if not weekly_volume or not exercise.muscle_groups:
                return 0.0
            
            # Check if any target muscle group has >20 sets
            for mg in exercise.muscle_groups:
                if mg.id in weekly_volume:
                    sets = weekly_volume[mg.id].get('total_sets', 0)
                    if sets > 20:
                        return 0.5  # Significant penalty for high volume muscle groups
                    elif sets > 10:
                        return 0.2  # Moderate penalty for moderate volume
            
            return 0.0
        
        # Helper function to calculate movement balance boost
        def get_movement_balance_boost(exercise: Exercise) -> float:
            """Return boost score (0.0-0.3) if exercise helps balance movement patterns"""
            if not movement_patterns:
                return 0.0
            
            boost = 0.0
            force_type_counts = movement_patterns.get('force_type', {})
            mechanics_counts = movement_patterns.get('mechanics', {})
            
            # Check force_type balance (Push/Pull)
            push_count = force_type_counts.get('Push', 0)
            pull_count = force_type_counts.get('Pull', 0)
            
            if exercise.force_type:
                exercise_force = exercise.force_type.strip()
                if push_count > pull_count + 1 and exercise_force == 'Pull':
                    boost += 0.15  # Boost Pull exercises when Push is overrepresented
                elif pull_count > push_count + 1 and exercise_force == 'Push':
                    boost += 0.15  # Boost Push exercises when Pull is overrepresented
            
            # Check mechanics balance (Compound/Isolation)
            compound_count = mechanics_counts.get('Compound', 0)
            isolation_count = mechanics_counts.get('Isolation', 0)
            
            if exercise.mechanics:
                exercise_mechanics = exercise.mechanics.strip()
                if compound_count > isolation_count + 1 and exercise_mechanics == 'Isolation':
                    boost += 0.15  # Boost Isolation exercises when Compound is overrepresented
                elif isolation_count > compound_count + 1 and exercise_mechanics == 'Compound':
                    boost += 0.15  # Boost Compound exercises when Isolation is overrepresented
            
            return min(0.3, boost)  # Cap boost at 0.3
        
        # Sort exercises considering weekly volume, frequency, and movement balance
        def sort_key(exercise: Exercise) -> tuple:
            """Sort key: (volume_penalty, -movement_boost, frequency) - lower is better"""
            volume_penalty = get_volume_penalty(exercise)
            movement_boost = get_movement_balance_boost(exercise)
            if user_workout_history and "exercise_frequency" in user_workout_history:
                freq = user_workout_history["exercise_frequency"].get(exercise.id, 0)
            else:
                freq = 0
            # Negative movement_boost so higher boost = better (lower sort value)
            return (volume_penalty, -movement_boost, freq)
        
        # Sort by volume penalty first (deprioritize high volume), then frequency
        exercises = sorted(exercises, key=sort_key)
        
        # Create recommendations
        recommendations = []
        for i, exercise in enumerate(exercises[:limit]):
            # Calculate priority score (higher for less frequent exercises, lower for high volume)
            base_score = 1.0 - (i * 0.1)  # Base decreasing priority
            
            if user_workout_history and "exercise_frequency" in user_workout_history:
                freq = user_workout_history["exercise_frequency"].get(exercise.id, 0)
                base_score = max(0.0, 1.0 - (freq * 0.1))  # Lower frequency = higher priority
            
            # Apply volume penalty and movement balance boost
            volume_penalty = get_volume_penalty(exercise)
            movement_boost = get_movement_balance_boost(exercise)
            priority_score = base_score * (1.0 - volume_penalty) + movement_boost
            
            # Get last performed date if available
            last_performed = None
            if user_workout_history and "last_performed" in user_workout_history:
                last_performed = user_workout_history["last_performed"].get(exercise.id)
            
            # Get weekly volume status
            volume_status = get_weekly_volume_status(exercise)
            
            # Determine if exercise helps balance movement patterns
            movement_balance = movement_boost > 0.0
            
            recommendations.append(
                ExerciseRecommendation(
                    exercise_id=exercise.id,
                    exercise_name=exercise.name,
                    priority_score=max(0.0, min(1.0, priority_score)),
                    reasoning=f"Rule-based recommendation based on muscle group targeting, equipment availability, and weekly volume management",
                    factors={
                        "frequency": "low" if not user_workout_history else "medium",
                        "last_performed": last_performed.isoformat() if last_performed else None,
                        "progression_opportunity": False,
                        "variety_boost": True,
                        "weekly_volume_status": volume_status,
                        "movement_balance": movement_balance,
                    },
                )
            )
        
        return RecommendationResponse(
            recommendations=recommendations,
            total_candidates=total_candidates,
            filtered_by_equipment=filtered_by_equipment,
            provider="fallback",
        )
