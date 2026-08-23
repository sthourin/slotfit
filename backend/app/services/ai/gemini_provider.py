"""
Gemini API provider implementation using the new google.genai package
"""
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.prompting import RecommendationPayload, build_context, create_prompt
from app.services.ai.candidates import fetch_candidates, ground_payload, muscle_group_names
from app.services.ai.base import AIProvider, RecommendationResponse, ExerciseRecommendation, NotRecommendedExercise

logger = get_logger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini API implementation of AI provider"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        # Only create Gemini client if API key is available
        api_key = settings.GEMINI_API_KEY
        if api_key and api_key.strip():
            try:
                # Use the new google.genai package
                self.client = genai.Client(api_key=api_key)
                # Model names must include "models/" prefix
                # Use gemini-2.5-flash (stable) or gemini-2.0-flash as fallback
                self.model_name = "models/gemini-2.5-flash"
            except Exception as e:
                logger.warning(f"Failed to create Gemini client: {e}")
                self.client = None
        else:
            self.client = None
        self.db = db
        # Set per request by get_exercise_recommendations and read by
        # _parse_response. Initialised so a parse without a preceding request
        # fails as "no recommendations" - routed to the fallback chain - rather
        # than as an AttributeError from somewhere unrelated.
        self._candidate_by_id: Dict[int, Any] = {}
        self._candidate_count: int = 0
    
    async def is_available(self) -> bool:
        """Check if Gemini API is available"""
        try:
            # Check if API key is set and not empty
            api_key = settings.GEMINI_API_KEY
            return bool(api_key and api_key.strip())
        except Exception:
            return False
    
    async def get_exercise_recommendations(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]] = None,
        weekly_volume: Optional[Dict[int, Dict[str, Any]]] = None,
        movement_patterns: Optional[Dict[str, Dict[str, int]]] = None,
        injury_restrictions: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations from Gemini API
        """
        logger.debug(f"GeminiProvider.get_exercise_recommendations called with mg_ids={muscle_group_ids}, eq_ids={available_equipment_ids}")
        
        if not await self.is_available():
            logger.debug("Gemini API not available, raising exception for service layer to handle")
            raise RuntimeError("Gemini API not available")
        
        # Grounded in the same candidate list as every other provider. Being
        # the fallback is not a licence to invent exercises - a fabricated
        # suggestion is worse here, because it only appears when something else
        # has already gone wrong and nobody is watching closely.
        if self.db is None:
            raise RuntimeError(
                "GeminiProvider needs a database session to ground recommendations "
                "in real exercises"
            )
        candidates, candidate_by_id = await fetch_candidates(
            self.db, muscle_group_ids, available_equipment_ids
        )
        if not candidates:
            raise ValueError(
                "No exercises match those muscle groups and equipment - nothing to rank"
            )
        names = await muscle_group_names(self.db, muscle_group_ids)
        self._candidate_by_id = candidate_by_id
        self._candidate_count = len(candidates)

        context = build_context(
            muscle_group_ids,
            available_equipment_ids,
            user_workout_history,
            weekly_volume,
            movement_patterns,
            injury_restrictions,
            candidates=candidates,
            muscle_group_names=names,
        )
        
        # Create prompt
        # Gemini parses free text here, so the shape must be spelled out.
        prompt = create_prompt(context, limit, include_json_shape=True)
        
        try:
            if not self.client:
                raise RuntimeError("Gemini client not initialized")
            
            logger.debug("Calling Gemini API...")
            # Call Gemini API using the new google.genai package
            # Try different model names if one fails (with models/ prefix)
            model_names = [
                "models/gemini-2.5-flash",  # Stable, fast
                "models/gemini-2.0-flash",   # Fallback
                "models/gemini-2.0-flash-001",  # Alternative
            ]
            response = None
            last_error = None
            
            for model in model_names:
                try:
                    logger.debug(f"Trying model: {model}")
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    logger.debug(f"Success with model: {model}")
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    # Don't retry on quota errors (429) - that's a billing issue
                    if "429" in error_msg or "quota" in error_msg.lower():
                        logger.warning(f"Quota exceeded for {model}, stopping retries")
                        raise
                    logger.debug(f"Model {model} failed: {error_msg[:100]}")
                    continue
            
            if response is None:
                raise RuntimeError(f"All models failed. Last error: {last_error}")
            
            # Parse response - the new API returns text via response.text
            response_text = response.text
            logger.debug(f"Gemini API response received, length: {len(response_text)}")
            result = await self._parse_response(response_text, limit, muscle_group_ids, available_equipment_ids)
            logger.debug(f"Parsed response: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
            return result
        
        except Exception as e:
            # Log the error and re-raise so service layer can try rule-based fallback
            logger.warning(f"Gemini API call failed: {e}", exc_info=True)
            raise  # Re-raise so service layer can handle fallback chain
    
    async def _parse_response(self, response_text: str, limit: int, muscle_group_ids: List[int], available_equipment_ids: List[int]) -> RecommendationResponse:
        """Parse Gemini API response"""
        try:
            # Extract JSON from response (handle markdown code blocks)
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Validated through the same schema the Claude path is constrained
            # to, then grounded against the same candidate list. Missing
            # `factors` keys fall back to their defaults rather than discarding
            # the recommendation.
            payload = RecommendationPayload.model_validate(json.loads(text))
            payload = ground_payload(payload, self._candidate_by_id, "gemini")

            recommendations = [
                ExerciseRecommendation(
                    exercise_id=item.exercise_id,
                    exercise_name=item.exercise_name,
                    priority_score=item.priority_score,
                    reasoning=item.reasoning,
                    factors=item.factors.model_dump(),
                )
                for item in payload.recommendations[:limit]
            ]
            not_recommended = [
                NotRecommendedExercise(
                    exercise_id=item.exercise_id,
                    exercise_name=item.exercise_name,
                    reason=item.reason,
                )
                for item in payload.not_recommended[:10]
            ]

            response = RecommendationResponse(
                recommendations=recommendations,
                not_recommended=not_recommended,
                # A fact about the query, counted rather than asked for.
                total_candidates=self._candidate_count,
                filtered_by_equipment=payload.filtered_by_equipment,
                provider="gemini",
            )
            
            # If Gemini returns empty recommendations, raise exception for service layer
            if response.total_candidates == 0 or len(response.recommendations) == 0:
                logger.warning("Gemini API returned empty recommendations, raising exception for service layer")
                raise ValueError("Gemini API returned empty recommendations")
            
            return response
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If parsing fails, re-raise so service layer can try rule-based fallback
            logger.error(f"Gemini API response parsing failed: {e}")
            logger.debug(f"Response text (first 500 chars): {response_text[:500]}")
            raise  # Re-raise so service layer can handle fallback chain
    
    async def _fallback_recommendations(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        limit: int,
    ) -> RecommendationResponse:
        """Fallback to rule-based recommendations when AI fails"""
        logger.debug(f"_fallback_recommendations called with mg_ids={muscle_group_ids}, eq_ids={available_equipment_ids}")
        logger.debug(f"Database session available: {self.db is not None}")
        
        if not self.db:
            logger.error("No database session available!")
            return RecommendationResponse(
                recommendations=[],
                total_candidates=0,
                filtered_by_equipment=0,
                provider="fallback",
            )
        
        # Import here to avoid circular dependency
        from app.services.ai.fallback_provider import FallbackProvider
        
        # Use FallbackProvider to get database-backed recommendations
        logger.debug("Creating FallbackProvider...")
        fallback = FallbackProvider(self.db)
        logger.debug("Calling FallbackProvider.get_exercise_recommendations...")
        result = await fallback.get_exercise_recommendations(
            muscle_group_ids=muscle_group_ids,
            available_equipment_ids=available_equipment_ids,
            user_workout_history=None,
            weekly_volume=None,
            movement_patterns=None,
            limit=limit,
        )
        logger.debug(f"FallbackProvider returned: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
        return result
