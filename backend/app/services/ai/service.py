"""
AI recommendation service
Handles provider selection and caching
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.services.ai.base import AIProvider, RecommendationResponse
from app.services.ai.claude_provider import ClaudeProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.fallback_provider import FallbackProvider
from app.models import WeeklyVolume, WorkoutSession, WorkoutExercise, Exercise
from sqlalchemy.orm import selectinload


class AIRecommendationService:
    """Service for managing AI exercise recommendations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._provider: Optional[AIProvider] = None
        self._cache: Dict[str, tuple[RecommendationResponse, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)  # 1 hour cache
    
    async def _get_provider(self) -> AIProvider:
        """Get the appropriate AI provider"""
        # Always check availability - don't cache provider
        # Priority: Claude -> Gemini -> Fallback
        
        if settings.AI_PROVIDER == "claude":
            claude_provider = ClaudeProvider(db=self.db)
            if await claude_provider.is_available():
                return claude_provider
        
        # Try Gemini as fallback
        gemini_provider = GeminiProvider(db=self.db)
        if await gemini_provider.is_available():
            return gemini_provider
        
        # Default to rule-based fallback
        return FallbackProvider(self.db)
    
    def _get_cache_key(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
    ) -> str:
        """Generate cache key"""
        mg_sorted = sorted(muscle_group_ids)
        eq_sorted = sorted(available_equipment_ids)
        return f"mg:{','.join(map(str, mg_sorted))}:eq:{','.join(map(str, eq_sorted))}"
    
    def _get_current_week_start(self) -> date:
        """Get the Monday date of the current week (ISO week start)"""
        today = date.today()
        # weekday() returns 0 for Monday, 6 for Sunday
        days_since_monday = today.weekday()
        return today - timedelta(days=days_since_monday)
    
    async def _get_weekly_volume(self) -> Dict[int, Dict[str, Any]]:
        """
        Query weekly volume for the current week
        
        Returns:
            Dict mapping muscle_group_id to volume data (total_sets, total_reps, total_volume)
        """
        week_start = self._get_current_week_start()
        
        query = select(WeeklyVolume).where(WeeklyVolume.week_start == week_start)
        result = await self.db.execute(query)
        volumes = result.scalars().all()
        
        volume_dict = {}
        for volume in volumes:
            volume_dict[volume.muscle_group_id] = {
                "total_sets": volume.total_sets,
                "total_reps": volume.total_reps,
                "total_volume": volume.total_volume,
            }
        
        return volume_dict
    
    async def _get_workout_movement_patterns(
        self,
        workout_session_id: Optional[int],
    ) -> Dict[str, Dict[str, int]]:
        """
        Calculate movement pattern counts from current workout session.
        
        Returns:
            Dict with keys:
            - 'force_type': {'Push': count, 'Pull': count, 'Other': count}
            - 'mechanics': {'Compound': count, 'Isolation': count}
            - 'movement_patterns': {pattern_name: count}
        """
        if not workout_session_id:
            return {
                'force_type': {},
                'mechanics': {},
                'movement_patterns': {},
            }
        
        # Query workout session with exercises
        query = select(WorkoutSession).where(
            WorkoutSession.id == workout_session_id
        ).options(
            selectinload(WorkoutSession.exercises).selectinload(WorkoutExercise.exercise)
        )
        result = await self.db.execute(query)
        workout = result.scalar_one_or_none()
        
        if not workout or not workout.exercises:
            return {
                'force_type': {},
                'mechanics': {},
                'movement_patterns': {},
            }
        
        # Count movement patterns
        force_type_counts: Dict[str, int] = {}
        mechanics_counts: Dict[str, int] = {}
        movement_pattern_counts: Dict[str, int] = {}
        
        for workout_exercise in workout.exercises:
            exercise = workout_exercise.exercise
            if not exercise:
                continue
            
            # Count force_type (Push/Pull/Other)
            if exercise.force_type:
                force_type = exercise.force_type.strip()
                if force_type:
                    force_type_counts[force_type] = force_type_counts.get(force_type, 0) + 1
            
            # Count mechanics (Compound/Isolation)
            if exercise.mechanics:
                mechanics = exercise.mechanics.strip()
                if mechanics:
                    mechanics_counts[mechanics] = mechanics_counts.get(mechanics, 0) + 1
            
            # Count movement patterns (movement_pattern_1, _2, _3)
            for pattern_field in [exercise.movement_pattern_1, exercise.movement_pattern_2, exercise.movement_pattern_3]:
                if pattern_field:
                    pattern = pattern_field.strip()
                    if pattern:
                        movement_pattern_counts[pattern] = movement_pattern_counts.get(pattern, 0) + 1
        
        return {
            'force_type': force_type_counts,
            'mechanics': mechanics_counts,
            'movement_patterns': movement_pattern_counts,
        }
    
    async def get_recommendations(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]] = None,
        workout_session_id: Optional[int] = None,
        limit: int = 5,
        use_cache: bool = True,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations with caching
        
        Args:
            muscle_group_ids: List of muscle group IDs for slot scope
            available_equipment_ids: List of available equipment IDs
            user_workout_history: Optional user workout history
            workout_session_id: Optional workout session ID to calculate movement pattern balance
            limit: Maximum number of recommendations
            use_cache: Whether to use cached results
            
        Returns:
            RecommendationResponse
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(muscle_group_ids, available_equipment_ids)
            if cache_key in self._cache:
                cached_response, cached_time = self._cache[cache_key]
                if datetime.now() - cached_time < self._cache_ttl:
                    return cached_response
                else:
                    # Remove expired cache
                    del self._cache[cache_key]
        
        # Query weekly volume for current week
        weekly_volume = await self._get_weekly_volume()
        
        # Calculate movement pattern balance from current workout
        movement_patterns = await self._get_workout_movement_patterns(workout_session_id)
        
        # Get provider (will return FallbackProvider if Claude not available)
        provider = await self._get_provider()
        print(f"DEBUG: Using provider: {type(provider).__name__}")
        
        response = None
        try:
            response = await provider.get_exercise_recommendations(
                muscle_group_ids=muscle_group_ids,
                available_equipment_ids=available_equipment_ids,
                user_workout_history=user_workout_history,
                weekly_volume=weekly_volume,
                movement_patterns=movement_patterns,
                limit=limit,
            )
            
            # If response is empty and we're not using fallback, try next provider in chain
            if response.total_candidates == 0 and not isinstance(provider, FallbackProvider):
                # Try Gemini if Claude failed
                if isinstance(provider, ClaudeProvider):
                    gemini_provider = GeminiProvider(db=self.db)
                    if await gemini_provider.is_available():
                        print("Claude returned empty results, trying Gemini...")
                        response = await gemini_provider.get_exercise_recommendations(
                            muscle_group_ids=muscle_group_ids,
                            available_equipment_ids=available_equipment_ids,
                            user_workout_history=user_workout_history,
                            weekly_volume=weekly_volume,
                            movement_patterns=movement_patterns,
                            limit=limit,
                        )
                
                # If still empty, use rule-based fallback
                if response.total_candidates == 0:
                    print("AI providers returned empty results, using rule-based fallback...")
                    fallback_provider = FallbackProvider(self.db)
                    response = await fallback_provider.get_exercise_recommendations(
                        muscle_group_ids=muscle_group_ids,
                        available_equipment_ids=available_equipment_ids,
                        user_workout_history=user_workout_history,
                        weekly_volume=weekly_volume,
                        movement_patterns=movement_patterns,
                        limit=limit,
                    )
        except Exception as e:
            # If provider fails, try next in chain
            import traceback
            print(f"ERROR: Provider failed: {e}")
            traceback.print_exc()
            
            # Try Gemini if Claude failed
            if isinstance(provider, ClaudeProvider):
                gemini_provider = GeminiProvider(db=self.db)
                if await gemini_provider.is_available():
                    print("Claude failed, trying Gemini...")
                    try:
                        response = await gemini_provider.get_exercise_recommendations(
                            muscle_group_ids=muscle_group_ids,
                            available_equipment_ids=available_equipment_ids,
                            user_workout_history=user_workout_history,
                            weekly_volume=weekly_volume,
                            movement_patterns=movement_patterns,
                            limit=limit,
                        )
                    except Exception as gemini_error:
                        print(f"Gemini also failed: {gemini_error}")
                        response = None
            
            # If Gemini also failed or wasn't available, use rule-based fallback
            if response is None or response.total_candidates == 0:
                print("Using rule-based fallback...")
                fallback_provider = FallbackProvider(self.db)
                response = await fallback_provider.get_exercise_recommendations(
                    muscle_group_ids=muscle_group_ids,
                    available_equipment_ids=available_equipment_ids,
                    user_workout_history=user_workout_history,
                    weekly_volume=weekly_volume,
                    limit=limit,
                )
        
        # Cache the response
        if use_cache:
            cache_key = self._get_cache_key(muscle_group_ids, available_equipment_ids)
            self._cache[cache_key] = (response, datetime.now())
        
        return response
