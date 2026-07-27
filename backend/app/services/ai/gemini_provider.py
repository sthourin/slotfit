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
from app.services.ai.base import (
    AIProvider,
    RecommendationResponse,
    ExerciseRecommendation,
    NotRecommendedExercise,
    WorkoutSuggestion,
)

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
        
        # Build context for the prompt
        context = self._build_context(
            muscle_group_ids,
            available_equipment_ids,
            user_workout_history,
            weekly_volume,
            movement_patterns,
            injury_restrictions,
        )
        
        # Create prompt
        prompt = self._create_prompt(context, limit)
        
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

    async def get_next_workout_suggestion(
        self,
        workout_history: Dict[str, Any],
        routine_options: List[Dict[str, Any]],
    ) -> WorkoutSuggestion:
        """Get next workout suggestion from Gemini API"""
        if not await self.is_available():
            logger.debug("Gemini API not available, raising exception for service layer to handle")
            raise RuntimeError("Gemini API not available")

        prompt = self._create_next_workout_prompt(workout_history, routine_options)

        try:
            if not self.client:
                raise RuntimeError("Gemini client not initialized")

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=1200,
                ),
            )

            response_text = response.text or ""
            suggestion = self._parse_next_workout_response(response_text, routine_options)
            suggestion.model = self.model_name
            suggestion.prompt = prompt
            return suggestion
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}", exc_info=True)
            raise
    
    def _build_context(
        self,
        muscle_group_ids: List[int],
        available_equipment_ids: List[int],
        user_workout_history: Optional[Dict[str, Any]],
        weekly_volume: Optional[Dict[int, Dict[str, Any]]],
        movement_patterns: Optional[Dict[str, Dict[str, int]]],
        injury_restrictions: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Build context for AI prompt"""
        return {
            "muscle_group_ids": muscle_group_ids,
            "available_equipment_ids": available_equipment_ids,
            "user_history": user_workout_history or {},
            "weekly_volume": weekly_volume or {},
            "movement_patterns": movement_patterns or {},
            "injury_restrictions": injury_restrictions or [],
        }

    def _create_next_workout_prompt(
        self,
        workout_history: Dict[str, Any],
        routine_options: List[Dict[str, Any]],
    ) -> str:
        """Create prompt for next workout suggestion using compact training summary"""
        # Format muscle group volume table
        mg_lines = []
        for mg in workout_history.get("muscle_groups", []):
            days = mg["days_since_trained"]
            days_str = f"{days}d ago" if days is not None else "never"
            mg_lines.append(
                f"  {mg['name']}: {mg['sets_7d']} sets/{mg['reps_7d']} reps (7d) | "
                f"{mg['sets_30d']} sets/{mg['reps_30d']} reps (30d) | last trained: {days_str}"
            )
        volume_text = "\n".join(mg_lines) if mg_lines else "  No training data available"

        # Format routine options
        routine_lines = []
        for r in routine_options:
            tags = ", ".join(r.get("tag_names", [])) if r.get("tag_names") else ""
            tag_str = f" [{tags}]" if tags else ""
            routine_lines.append(
                f"  - {r['name']} (id: {r['id']}, type: {r.get('routine_type', 'N/A')}, "
                f"style: {r.get('workout_style', 'N/A')}, slots: {r.get('slot_count', 0)}){tag_str}"
            )
        routines_text = "\n".join(routine_lines) if routine_lines else "  No routines configured"

        sessions_7d = workout_history.get("sessions_7d", 0)
        sessions_30d = workout_history.get("sessions_30d", 0)
        avg_per_week = workout_history.get("avg_sessions_per_week", 0)

        # Build schedule context section
        weekly_counts = workout_history.get("weekly_counts", [])
        schedule_pattern = workout_history.get("schedule_pattern", "unknown")
        planned_sessions = workout_history.get("planned_sessions")

        weekly_str = ", ".join(str(w) for w in weekly_counts) if weekly_counts else "no data"
        schedule_text = (
            f"SCHEDULE CONTEXT:\n"
            f"  Historical average: ~{avg_per_week} sessions/week ({schedule_pattern} pattern: {weekly_str} over last 4 weeks)\n"
        )
        if planned_sessions is not None:
            schedule_text += f"  Planned sessions this week: {planned_sessions}\n"
            if planned_sessions <= 3:
                schedule_text += "  -> With limited sessions, prefer full-body routines that maximize muscle group coverage.\n"
            else:
                schedule_text += "  -> With more sessions available, split routines can be effective for focused volume.\n"
        else:
            if avg_per_week <= 3:
                schedule_text += "  -> Training frequency is low; prefer full-body routines for balanced coverage.\n"
            else:
                schedule_text += "  -> Training frequency supports split routines for focused volume.\n"

        # Build exercise database section for name grounding
        exercise_names = workout_history.get("available_exercise_names", [])
        if exercise_names:
            exercise_db_text = (
                "EXERCISE DATABASE (you MUST choose suggested_exercises from this list, using exact names):\n"
                f"  {', '.join(exercise_names)}\n\n"
            )
        else:
            exercise_db_text = ""

        return (
            "You are a Certified Athletic Trainer (ATC) with CSCS experience at the professional athletics level. "
            "Program training based on volume, periodization, and recovery principles. "
            "Apply your ATC background to flag contraindicated exercises for any active injuries.\n"
            "Based on the training summary below, suggest the best next workout.\n"
            "Consider muscle group recovery (48-72h between direct work), training balance, frequency, and schedule.\n"
            "Output ONLY valid JSON.\n\n"
            f"TRAINING FREQUENCY:\n"
            f"  {sessions_7d} sessions in last 7 days, {sessions_30d} in last 30 days\n\n"
            f"{schedule_text}\n"
            f"VOLUME BY MUSCLE GROUP (sets/reps over 7 days and 30 days, with recovery status):\n"
            f"{volume_text}\n\n"
            f"AVAILABLE ROUTINES:\n"
            f"{routines_text}\n\n"
            f"{exercise_db_text}"
            "Suggest the next workout prioritizing undertrained muscle groups, adequate recovery, and the user's schedule.\n"
            "Return JSON with fields:\n"
            "{\n"
            '  "suggested_routine_id": number | null,\n'
            '  "suggested_routine_name": string | null,\n'
            '  "focus": string describing the workout focus (e.g. "Lower Body Strength", "Pull Day"),\n'
            '  "rationale": string explaining why based on the training data,\n'
            '  "suggested_exercises": [string] list of 4-8 exercise names from the EXERCISE DATABASE above\n'
            "}\n"
        )

    def _parse_next_workout_response(
        self,
        response_text: str,
        routine_options: List[Dict[str, Any]],
    ) -> WorkoutSuggestion:
        """Parse the next workout suggestion response"""
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            try:
                start = response_text.index("{")
                end = response_text.rindex("}") + 1
                data = json.loads(response_text[start:end])
            except Exception:
                logger.warning("Failed to parse Gemini next workout response as JSON")
                data = {}

        routine_id_set = {r.get("id") for r in routine_options}
        suggested_routine_id = data.get("suggested_routine_id")
        suggested_routine_name = data.get("suggested_routine_name")

        if suggested_routine_id not in routine_id_set:
            matched = None
            if suggested_routine_name:
                matched = next(
                    (r for r in routine_options if r.get("name", "").lower() == suggested_routine_name.lower()),
                    None,
                )
            if matched:
                suggested_routine_id = matched.get("id")
                suggested_routine_name = matched.get("name")
            else:
                suggested_routine_id = None

        return WorkoutSuggestion(
            suggested_routine_id=suggested_routine_id,
            suggested_routine_name=suggested_routine_name,
            focus=data.get("focus"),
            rationale=data.get("rationale") or "Suggested based on your recent workout history.",
            suggested_exercises=data.get("suggested_exercises") or [],
        )
    
    def _create_prompt(self, context: Dict[str, Any], limit: int) -> str:
        """Create prompt for Gemini API"""
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
        
        # Build injury restrictions context
        injury_note = ""
        injury_restrictions = context.get('injury_restrictions', [])
        if injury_restrictions:
            injury_lines = []
            for restriction in injury_restrictions:
                injury_lines.append(
                    f"  - {restriction['injury_name']} (severity: {restriction['severity']}): "
                    f"Avoid {restriction['restriction_type']} = '{restriction['restriction_value']}'"
                )
            injury_note = f"""

User Injuries:
The user has the following active injuries. DO NOT recommend exercises that may aggravate these conditions:
{chr(10).join(injury_lines)}

For any exercise that could aggravate an injury, include it in the not_recommended array with reason "May aggravate [injury name]".
IMPORTANT: This feature helps avoid potentially problematic exercises but is NOT medical advice. When in doubt, exclude the exercise (safety first)."""
        
        return f"""You are an expert fitness coach helping to recommend exercises for a workout slot.

Context:
- Target muscle groups: {context['muscle_group_ids']} (exercises MUST target ALL of these groups, not just one)
- Available equipment: {context['available_equipment_ids']}
- User workout history: {json.dumps(context['user_history'], indent=2) if context['user_history'] else 'None'}
- Current week's training volume per muscle group:
{weekly_volume_text}
- Current workout's movement pattern balance:
{movement_balance_text}{injury_note}

Task:
Provide {limit} exercise recommendations prioritized based on:
1. Muscle group targeting accuracy (exercises must target ALL specified muscle groups, not just one)
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
                "movement_balance": <boolean>  # true if this exercise helps balance the workout's movement patterns
            }}
        }}
    ],
    "not_recommended": [
        {{
            "exercise_id": <integer>,
            "exercise_name": "<string>",
            "reason": "<string>"  # Human-readable explanation (e.g., "Equipment not available: Cable Machine", "Weekly volume exceeded for Chest (22 sets)", "Performed 1 day ago - insufficient recovery")
        }}
    ],
    "total_candidates": <integer>,
    "filtered_by_equipment": <integer>
}}

The "not_recommended" array should include exercises that were filtered out, with clear reasons:
- Equipment not available: {{equipment_name}}
- Weekly volume exceeded for {{muscle_group}} ({{X}} sets)
- Performed {{X}} days ago - insufficient recovery
- Does not target selected muscle groups
- May aggravate {{injury_name}} (if exercise matches injury restrictions)

Limit not_recommended to ~10 entries with diverse reason types.

The weekly_volume_status factor should indicate the current week's volume for the primary muscle group(s) targeted by the exercise:
- "low": <10 sets/week
- "moderate": 10-20 sets/week
- "high": >20 sets/week

The movement_balance factor should be true if this exercise helps balance the workout (e.g., adding a Pull exercise when Push is overrepresented, or adding Isolation when Compound is overrepresented).

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
            
            # Parse not_recommended array (if present)
            not_recommended_data = data.get("not_recommended", [])
            not_recommended = [
                NotRecommendedExercise(**entry) for entry in not_recommended_data
            ]
            
            response = RecommendationResponse(
                recommendations=recommendations[:limit],
                not_recommended=not_recommended[:10],  # Limit to 10 entries
                total_candidates=data.get("total_candidates", len(recommendations)),
                filtered_by_equipment=data.get("filtered_by_equipment", len(recommendations)),
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
