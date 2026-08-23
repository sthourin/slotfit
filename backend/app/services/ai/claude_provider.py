"""
Claude API provider implementation
"""
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import get_logger
from app.services.ai.base import AIProvider, RecommendationResponse, ExerciseRecommendation, NotRecommendedExercise
from app.services.ai.prompting import RecommendationPayload, build_context, create_prompt
from app.services.ai.candidates import fetch_candidates, ground_payload, muscle_group_names

logger = get_logger(__name__)


class ClaudeProvider(AIProvider):
    """Claude API implementation of AI provider"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        # Only create Anthropic client if API key is available
        api_key = settings.ANTHROPIC_API_KEY
        if api_key and api_key.strip():
            try:
                self.client = Anthropic(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to create Anthropic client: {e}")
                self.client = None
        else:
            self.client = None
        self.model = settings.AI_MODEL
        self.db = db
    
    async def is_available(self) -> bool:
        """Check if Claude API is available"""
        try:
            # Check if API key is set and not empty
            api_key = settings.ANTHROPIC_API_KEY
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
        Get exercise recommendations from Claude API
        """
        logger.debug(f"ClaudeProvider.get_exercise_recommendations called with mg_ids={muscle_group_ids}, eq_ids={available_equipment_ids}")
        
        if not await self.is_available():
            logger.debug("Claude API not available, raising exception for service layer to handle")
            raise RuntimeError("Claude API not available")
        
        # The catalogue the model must choose from. Without it the model
        # invents exercises and ids that look real; with it, every suggestion is
        # something the user can actually walk up to and do.
        if self.db is None:
            raise RuntimeError(
                "ClaudeProvider needs a database session to ground recommendations "
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
        prompt = create_prompt(context, limit)
        
        try:
            if not self.client:
                raise RuntimeError("Anthropic client not initialized")
            
            logger.debug(f"Calling Claude API (model={self.model})...")
            # `parse` constrains the response to RecommendationPayload and
            # validates it, so there is no JSON to hand-extract and no markdown
            # fence to strip - the old parser failed outright whenever the model
            # wrapped its answer in a sentence.
            message = self.client.messages.parse(
                model=self.model,
                max_tokens=settings.AI_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                output_format=RecommendationPayload,
            )

            # A refusal is HTTP 200 with stop_reason "refusal" and no usable
            # content - not an exception. Raising here routes it into the same
            # provider fallback chain as any other failure, which is what should
            # happen: the user still gets recommendations, from Gemini or the
            # rule-based provider.
            if message.stop_reason == "refusal":
                category = getattr(message.stop_details, "category", None)
                raise RuntimeError(f"Claude declined the request (category={category})")

            grounded = ground_payload(message.parsed_output, candidate_by_id, "claude")
            result = self._to_response(grounded, limit, len(candidates))
            logger.debug(f"Parsed response: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
            return result
        
        except Exception as e:
            # Log the error and re-raise so service layer can try Gemini
            logger.warning(f"Claude API call failed: {e}", exc_info=True)
            raise  # Re-raise so service layer can handle fallback chain
    
    def _to_response(
        self, payload: RecommendationPayload, limit: int, candidate_count: int
    ) -> RecommendationResponse:
        """Validated model output -> the app's response type.

        `not_recommended` is capped at 10: it powers an expandable "Why Not"
        section, and a longer list is scrolling, not explanation.
        """
        recommendations = [
            ExerciseRecommendation(
                exercise_id=item.exercise_id,
                exercise_name=item.exercise_name,
                priority_score=item.priority_score,
                reasoning=item.reasoning,
                # Back to a plain dict: the web client reads these keys loosely
                # and other providers emit a dict too.
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

        # An empty recommendation list is a failure, not a result - the slot
        # still needs exercises, so it goes to the fallback chain.
        if not recommendations:
            raise ValueError("Claude returned no recommendations")

        return RecommendationResponse(
            recommendations=recommendations,
            not_recommended=not_recommended,
            # Counted here, not taken from the model. It is a fact about the
            # query, and a model asked to report it simply guesses.
            total_candidates=candidate_count,
            filtered_by_equipment=payload.filtered_by_equipment,
            provider="claude",
        )

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