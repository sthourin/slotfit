"""
Gemini API provider implementation using the new google.genai package
"""
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.ai.base import AIProvider, RecommendationResponse, ExerciseRecommendation


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
                print(f"Warning: Failed to create Gemini client: {e}")
                self.client = None
        else:
            self.client = None
        self.db = db
    
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
        limit: int = 5,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations from Gemini API
        """
        print(f"GeminiProvider.get_exercise_recommendations called with mg_ids={muscle_group_ids}, eq_ids={available_equipment_ids}")
        
        if not await self.is_available():
            print("Gemini API not available, raising exception for service layer to handle")
            raise RuntimeError("Gemini API not available")
        
        # Build context for the prompt
        context = self._build_context(
            muscle_group_ids,
            available_equipment_ids,
            user_workout_history,
        )
        
        # Create prompt
        prompt = self._create_prompt(context, limit)
        
        try:
            if not self.client:
                raise RuntimeError("Gemini client not initialized")
            
            print("Calling Gemini API...")
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
                    print(f"Trying model: {model}")
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    print(f"Success with model: {model}")
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    # Don't retry on quota errors (429) - that's a billing issue
                    if "429" in error_msg or "quota" in error_msg.lower():
                        print(f"Quota exceeded for {model}, stopping retries")
                        raise
                    print(f"Model {model} failed: {error_msg[:100]}")
                    continue
            
            if response is None:
                raise RuntimeError(f"All models failed. Last error: {last_error}")
            
            # Parse response - the new API returns text via response.text
            response_text = response.text
            print(f"Gemini API response received, length: {len(response_text)}")
            result = await self._parse_response(response_text, limit, muscle_group_ids, available_equipment_ids)
            print(f"Parsed response: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
            return result
        
        except Exception as e:
            # Log the error and re-raise so service layer can try rule-based fallback
            print(f"Gemini API call failed: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise so service layer can handle fallback chain
    
    def _build_context(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build context for AI prompt"""
        return {
            "muscle_group_ids": muscle_group_ids,
            "available_equipment_ids": available_equipment_ids,
            "user_history": user_workout_history or {},
        }
    
    def _create_prompt(self, context: Dict[str, Any], limit: int) -> str:
        """Create prompt for Gemini API"""
        return f"""You are an expert fitness coach helping to recommend exercises for a workout slot.

Context:
- Target muscle groups: {context['muscle_group_ids']}
- Available equipment: {context['available_equipment_ids']}
- User workout history: {json.dumps(context['user_history'], indent=2) if context['user_history'] else 'None'}

Task:
Provide {limit} exercise recommendations prioritized based on:
1. Muscle group targeting accuracy
2. Equipment availability match
3. User's past performance and progression opportunities
4. Workout variety (avoid recent exercises for variety)

Return your response as a JSON object with this exact structure:
{{
    "recommendations": [
        {{
            "exercise_id": <integer>,
            "exercise_name": "<string>",
            "priority_score": <float 0.0-1.0>,
            "reasoning": "<brief explanation>",
            "factors": {{
                "frequency": "<low|medium|high>",
                "last_performed": "<ISO8601 date or null>",
                "progression_opportunity": <boolean>,
                "variety_boost": <boolean>
            }}
        }}
    ],
    "total_candidates": <integer>,
    "filtered_by_equipment": <integer>
}}

Only return valid JSON, no additional text."""
    
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
            
            data = json.loads(text)
            
            recommendations = [
                ExerciseRecommendation(**rec) for rec in data.get("recommendations", [])
            ]
            
            response = RecommendationResponse(
                recommendations=recommendations[:limit],
                total_candidates=data.get("total_candidates", len(recommendations)),
                filtered_by_equipment=data.get("filtered_by_equipment", len(recommendations)),
                provider="gemini",
            )
            
            # If Gemini returns empty recommendations, raise exception for service layer
            if response.total_candidates == 0 or len(response.recommendations) == 0:
                print(f"Gemini API returned empty recommendations, raising exception for service layer")
                raise ValueError("Gemini API returned empty recommendations")
            
            return response
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If parsing fails, re-raise so service layer can try rule-based fallback
            print(f"Gemini API response parsing failed: {e}")
            print(f"Response text (first 500 chars): {response_text[:500]}")
            raise  # Re-raise so service layer can handle fallback chain
    
    async def _fallback_recommendations(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        limit: int,
    ) -> RecommendationResponse:
        """Fallback to rule-based recommendations when AI fails"""
        print(f"_fallback_recommendations called with mg_ids={muscle_group_ids}, eq_ids={available_equipment_ids}")
        print(f"Database session available: {self.db is not None}")
        
        if not self.db:
            print("ERROR: No database session available!")
            return RecommendationResponse(
                recommendations=[],
                total_candidates=0,
                filtered_by_equipment=0,
                provider="fallback",
            )
        
        # Import here to avoid circular dependency
        from app.services.ai.fallback_provider import FallbackProvider
        
        # Use FallbackProvider to get database-backed recommendations
        print("Creating FallbackProvider...")
        fallback = FallbackProvider(self.db)
        print("Calling FallbackProvider.get_exercise_recommendations...")
        result = await fallback.get_exercise_recommendations(
            muscle_group_ids=muscle_group_ids,
            available_equipment_ids=available_equipment_ids,
            user_workout_history=None,
            limit=limit,
        )
        print(f"FallbackProvider returned: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
        return result
