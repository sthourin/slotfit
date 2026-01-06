"""
Base AI provider interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ExerciseRecommendation(BaseModel):
    """Single exercise recommendation"""
    exercise_id: int
    exercise_name: str
    priority_score: float  # 0.0-1.0
    reasoning: str
    factors: Dict[str, Any]


class RecommendationResponse(BaseModel):
    """AI recommendation response"""
    recommendations: List[ExerciseRecommendation]
    total_candidates: int
    filtered_by_equipment: int
    provider: Optional[str] = None  # "claude", "fallback", etc. - indicates which provider generated the recommendations


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
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
        Get exercise recommendations for a slot
        
        Args:
            muscle_group_ids: List of muscle group IDs for slot scope
            available_equipment_ids: List of available equipment IDs
            user_workout_history: Optional user workout history data
            weekly_volume: Optional dict mapping muscle_group_id to volume data (total_sets, total_reps, total_volume)
            movement_patterns: Optional dict with force_type, mechanics, and movement_patterns counts from current workout
            limit: Maximum number of recommendations to return
            
        Returns:
            RecommendationResponse with prioritized exercises
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if AI service is available"""
        pass
