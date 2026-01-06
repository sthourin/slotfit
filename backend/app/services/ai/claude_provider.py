"""
Claude API provider implementation
"""
import json
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.services.ai.base import AIProvider, RecommendationResponse, ExerciseRecommendation


class ClaudeProvider(AIProvider):
    """Claude API implementation of AI provider"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        # Only create Anthropic client if API key is available
        api_key = settings.ANTHROPIC_API_KEY
        if api_key and api_key.strip():
            try:
                self.client = Anthropic(api_key=api_key)
            except Exception as e:
                print(f"Warning: Failed to create Anthropic client: {e}")
                self.client = None
        else:
            self.client = None
        self.model = "claude-3-sonnet-20240229"  # Can be made configurable
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
        limit: int = 5,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations from Claude API
        """
        print(f"ClaudeProvider.get_exercise_recommendations called with mg_ids={muscle_group_ids}, eq_ids={available_equipment_ids}")
        
        if not await self.is_available():
            print("Claude API not available, raising exception for service layer to handle")
            raise RuntimeError("Claude API not available")
        
        # Build context for the prompt
        context = self._build_context(
            muscle_group_ids,
            available_equipment_ids,
            user_workout_history,
            weekly_volume,
            movement_patterns,
        )
        
        # Create prompt
        prompt = self._create_prompt(context, limit)
        
        try:
            if not self.client:
                raise RuntimeError("Anthropic client not initialized")
            
            print("Calling Claude API...")
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            
            # Parse response
            response_text = message.content[0].text
            print(f"Claude API response received, length: {len(response_text)}")
            result = await self._parse_response(response_text, limit, muscle_group_ids, available_equipment_ids)
            print(f"Parsed response: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
            return result
        
        except Exception as e:
            # Log the error and re-raise so service layer can try Gemini
            print(f"Claude API call failed: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise so service layer can handle fallback chain
    
    def _build_context(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]],
        weekly_volume: Optional[Dict[int, Dict[str, Any]]],
        movement_patterns: Optional[Dict[str, Dict[str, int]]],
    ) -> Dict[str, Any]:
        """Build context for AI prompt"""
        return {
            "muscle_group_ids": muscle_group_ids,
            "available_equipment_ids": available_equipment_ids,
            "user_history": user_workout_history or {},
            "weekly_volume": weekly_volume or {},
            "movement_patterns": movement_patterns or {},
        }
    
    def _create_prompt(self, context: Dict[str, Any], limit: int) -> str:
        """Create prompt for Claude API"""
        weekly_volume = context.get('weekly_volume', {})
        
        # Build weekly volume context string
        weekly_volume_text = "None"
        if weekly_volume:
            volume_lines = []
            for mg_id, volume_data in weekly_volume.items():
                sets = volume_data.get('total_sets', 0)
                status = "high" if sets > 20 else "moderate" if sets > 10 else "low"
                volume_lines.append(f"  - Muscle group {mg_id}: {sets} sets/week ({status} volume)")
            weekly_volume_text = "\n".join(volume_lines) if volume_lines else "None"
        
        # Check if any target muscle groups have high volume (>20 sets/week)
        target_mg_ids = context.get('muscle_group_ids', [])
        high_volume_mgs = [
            mg_id for mg_id in target_mg_ids 
            if mg_id in weekly_volume and weekly_volume[mg_id].get('total_sets', 0) > 20
        ]
        
        deprioritize_note = ""
        if high_volume_mgs:
            deprioritize_note = f"\n\nIMPORTANT: The following target muscle groups have exceeded 20 sets this week and should be DEPRIORITIZED: {high_volume_mgs}. Consider recommending exercises that target other muscle groups or lighter variations."
        
        # Build movement pattern balance context
        movement_patterns = context.get('movement_patterns', {})
        movement_balance_text = "None"
        if movement_patterns:
            force_type_counts = movement_patterns.get('force_type', {})
            mechanics_counts = movement_patterns.get('mechanics', {})
            pattern_counts = movement_patterns.get('movement_patterns', {})
            
            balance_lines = []
            if force_type_counts:
                balance_lines.append(f"Force Type Balance: {json.dumps(force_type_counts, indent=2)}")
            if mechanics_counts:
                balance_lines.append(f"Mechanics Balance: {json.dumps(mechanics_counts, indent=2)}")
            if pattern_counts:
                balance_lines.append(f"Movement Patterns: {json.dumps(pattern_counts, indent=2)}")
            
            if balance_lines:
                movement_balance_text = "\n".join(balance_lines)
        
        # Determine underrepresented patterns to boost
        boost_note = ""
        if movement_patterns:
            force_type_counts = movement_patterns.get('force_type', {})
            mechanics_counts = movement_patterns.get('mechanics', {})
            
            push_count = force_type_counts.get('Push', 0)
            pull_count = force_type_counts.get('Pull', 0)
            compound_count = mechanics_counts.get('Compound', 0)
            isolation_count = mechanics_counts.get('Isolation', 0)
            
            boost_suggestions = []
            if push_count > pull_count + 1:
                boost_suggestions.append("PULL exercises")
            elif pull_count > push_count + 1:
                boost_suggestions.append("PUSH exercises")
            
            if compound_count > isolation_count + 1:
                boost_suggestions.append("ISOLATION exercises")
            elif isolation_count > compound_count + 1:
                boost_suggestions.append("COMPOUND exercises")
            
            if boost_suggestions:
                boost_note = f"\n\nMOVEMENT BALANCE: The current workout has an imbalance. Consider boosting: {', '.join(boost_suggestions)} to achieve better balance."
        
        return f"""You are an expert fitness coach helping to recommend exercises for a workout slot.

Context:
- Target muscle groups: {context['muscle_group_ids']}
- Available equipment: {context['available_equipment_ids']}
- User workout history: {json.dumps(context['user_history'], indent=2) if context['user_history'] else 'None'}
- Current week's training volume per muscle group:
{weekly_volume_text}
- Current workout's movement pattern balance:
{movement_balance_text}

Task:
Provide {limit} exercise recommendations prioritized based on:
1. Muscle group targeting accuracy
2. Equipment availability match
3. User's past performance and progression opportunities
4. Workout variety (avoid recent exercises for variety)
5. Weekly volume management (deprioritize muscle groups with >20 sets/week to prevent overtraining)
6. Movement pattern balance (balance push/pull and compound/isolation exercises){deprioritize_note}{boost_note}

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
                "variety_boost": <boolean>,
                "weekly_volume_status": "<low|moderate|high>",
                "movement_balance": "<boolean>"  # true if this exercise helps balance the workout's movement patterns
            }}
        }}
    ],
    "total_candidates": <integer>,
    "filtered_by_equipment": <integer>
}}

The weekly_volume_status factor should indicate the current week's volume for the primary muscle group(s) targeted by the exercise:
- "low": <10 sets/week
- "moderate": 10-20 sets/week
- "high": >20 sets/week

The movement_balance factor should be true if this exercise helps balance the workout (e.g., adding a Pull exercise when Push is overrepresented, or adding Isolation when Compound is overrepresented).

Only return valid JSON, no additional text."""
    
    async def _parse_response(self, response_text: str, limit: int, muscle_group_ids: List[int], available_equipment_ids: List[int]) -> RecommendationResponse:
        """Parse Claude API response"""
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
            
            # Ensure weekly_volume_status and movement_balance are present in factors (for backward compatibility)
            recommendations_data = data.get("recommendations", [])
            for rec in recommendations_data:
                if "factors" not in rec:
                    rec["factors"] = {}
                if "weekly_volume_status" not in rec["factors"]:
                    rec["factors"]["weekly_volume_status"] = "low"  # Default to low if missing
                if "movement_balance" not in rec["factors"]:
                    rec["factors"]["movement_balance"] = False  # Default to false if missing
            
            recommendations = [
                ExerciseRecommendation(**rec) for rec in recommendations_data
            ]
            
            response = RecommendationResponse(
                recommendations=recommendations[:limit],
                total_candidates=data.get("total_candidates", len(recommendations)),
                filtered_by_equipment=data.get("filtered_by_equipment", len(recommendations)),
                provider="claude",
            )
            
            # If Claude returns empty recommendations, raise exception for service layer
            if response.total_candidates == 0 or len(response.recommendations) == 0:
                print(f"Claude API returned empty recommendations, raising exception for service layer")
                raise ValueError("Claude API returned empty recommendations")
            
            return response
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # If parsing fails, re-raise so service layer can try Gemini
            print(f"Claude API response parsing failed: {e}")
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
            weekly_volume=None,
            movement_patterns=None,
            limit=limit,
        )
        print(f"FallbackProvider returned: total_candidates={result.total_candidates}, recommendations={len(result.recommendations)}")
        return result