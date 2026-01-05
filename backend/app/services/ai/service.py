"""
AI recommendation service
Handles provider selection and caching
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai.base import AIProvider, RecommendationResponse
from app.services.ai.claude_provider import ClaudeProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.fallback_provider import FallbackProvider


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
    
    async def get_recommendations(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        use_cache: bool = True,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations with caching
        
        Args:
            muscle_group_ids: List of muscle group IDs for slot scope
            available_equipment_ids: List of available equipment IDs
            user_workout_history: Optional user workout history
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
        
        # Get provider (will return FallbackProvider if Claude not available)
        provider = await self._get_provider()
        print(f"DEBUG: Using provider: {type(provider).__name__}")
        
        response = None
        try:
            response = await provider.get_exercise_recommendations(
                muscle_group_ids=muscle_group_ids,
                available_equipment_ids=available_equipment_ids,
                user_workout_history=user_workout_history,
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
                    limit=limit,
                )
        
        # Cache the response
        if use_cache:
            cache_key = self._get_cache_key(muscle_group_ids, available_equipment_ids)
            self._cache[cache_key] = (response, datetime.now())
        
        return response
