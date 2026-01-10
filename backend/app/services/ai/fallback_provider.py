"""
Fallback rule-based recommendation provider
Used when AI is unavailable
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.services.ai.base import AIProvider, RecommendationResponse, ExerciseRecommendation, NotRecommendedExercise
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
        injury_restrictions: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
    ) -> RecommendationResponse:
        """
        Get exercise recommendations using rule-based logic
        """
        # Step 1: Query ALL exercises matching muscle groups (before equipment filter)
        # This allows us to track which exercises get filtered out and why
        query_all = select(Exercise).options(
            selectinload(Exercise.primary_equipment),
            selectinload(Exercise.secondary_equipment),
            selectinload(Exercise.muscle_groups),
        )
        
        # Filter by muscle groups only
        if muscle_group_ids:
            query_all = query_all.join(
                exercise_muscle_groups,
                Exercise.id == exercise_muscle_groups.c.exercise_id
            ).where(
                exercise_muscle_groups.c.muscle_group_id.in_(muscle_group_ids)
            ).distinct()
        
        # Execute query to get all muscle-group-matching exercises
        result_all = await self.db.execute(query_all)
        all_exercises = result_all.scalars().unique().all()
        
        total_candidates = len(all_exercises)
        
        # Helper function to check if exercise is restricted by injury
        def is_restricted_by_injury(exercise: Exercise, restrictions: List[Dict]) -> Optional[str]:
            """Check if exercise matches any injury restriction. Returns reason if restricted."""
            if not restrictions:
                return None
            
            for r in restrictions:
                # Check movement pattern restrictions
                if r["restriction_type"] == "movement_pattern":
                    patterns = [exercise.movement_pattern_1, exercise.movement_pattern_2, exercise.movement_pattern_3]
                    if any(r["restriction_value"].lower() in (p or "").lower() for p in patterns):
                        return f"May aggravate {r['injury_name']}"
                
                # Check force type restrictions
                elif r["restriction_type"] == "force_type":
                    if exercise.force_type and r["restriction_value"].lower() in exercise.force_type.lower():
                        return f"May aggravate {r['injury_name']}"
                
                # Check posture restrictions
                elif r["restriction_type"] == "posture":
                    if exercise.posture and r["restriction_value"].lower() in exercise.posture.lower():
                        return f"May aggravate {r['injury_name']}"
                
                # Check plane of motion restrictions
                elif r["restriction_type"] == "plane_of_motion":
                    planes = [exercise.plane_of_motion_1, exercise.plane_of_motion_2, exercise.plane_of_motion_3]
                    if any(r["restriction_value"].lower() in (p or "").lower() for p in planes):
                        return f"May aggravate {r['injury_name']}"
                
                # Check laterality restrictions
                elif r["restriction_type"] == "laterality":
                    if exercise.laterality and r["restriction_value"].lower() in exercise.laterality.lower():
                        return f"May aggravate {r['injury_name']}"
            
            return None
        
        # Step 2: Build not_recommended list by tracking filtered exercises
        not_recommended: List[NotRecommendedExercise] = []
        recommended_exercise_ids = set()
        
        # Track exercises that don't match muscle groups (shouldn't happen if query is correct, but check anyway)
        # This is mainly for exercises that might have been in a broader query
        
        # Step 3: Apply injury filter first (before equipment)
        # Check each exercise against injury restrictions
        injury_filtered_exercises = []
        for exercise in all_exercises:
            injury_reason = is_restricted_by_injury(exercise, injury_restrictions or [])
            if injury_reason:
                not_recommended.append(NotRecommendedExercise(
                    exercise_id=exercise.id,
                    exercise_name=exercise.name,
                    reason=injury_reason
                ))
            else:
                injury_filtered_exercises.append(exercise)
        
        # Step 4: Apply equipment filter (with bodyweight exception)
        # Bodyweight exercises (primary_equipment_id IS NULL) are ALWAYS included
        available_exercises = []
        filtered_by_equipment_count = 0
        
        for exercise in injury_filtered_exercises:
            # Check if exercise matches equipment requirements
            is_bodyweight = exercise.primary_equipment_id is None
            has_available_equipment = False
            
            if is_bodyweight:
                # Bodyweight exercises are always available
                has_available_equipment = True
            elif available_equipment_ids:
                # Check if exercise uses available equipment
                has_available_equipment = (
                    exercise.primary_equipment_id in available_equipment_ids or
                    exercise.secondary_equipment_id in available_equipment_ids
                )
            else:
                # No equipment filter specified, all exercises are available
                has_available_equipment = True
            
            if has_available_equipment:
                available_exercises.append(exercise)
            else:
                # Exercise filtered by equipment - add to not_recommended
                filtered_by_equipment_count += 1
                equipment_name = "Unknown Equipment"
                if exercise.primary_equipment:
                    equipment_name = exercise.primary_equipment.name
                elif exercise.secondary_equipment:
                    equipment_name = exercise.secondary_equipment.name
                
                not_recommended.append(
                    NotRecommendedExercise(
                        exercise_id=exercise.id,
                        exercise_name=exercise.name,
                        reason=f"Equipment not available: {equipment_name}"
                    )
                )
        
        # Step 5: Check weekly volume for available exercises
        for exercise in available_exercises:
            if weekly_volume and exercise.muscle_groups:
                for mg in exercise.muscle_groups:
                    if mg.id in weekly_volume:
                        sets = weekly_volume[mg.id].get('total_sets', 0)
                        if sets > 20:
                            # High volume - add to not_recommended if not already recommended
                            if exercise.id not in recommended_exercise_ids:
                                mg_name = mg.name if mg.name else f"Muscle Group {mg.id}"
                                not_recommended.append(
                                    NotRecommendedExercise(
                                        exercise_id=exercise.id,
                                        exercise_name=exercise.name,
                                        reason=f"Weekly volume exceeded for {mg_name} ({sets} sets)"
                                    )
                                )
                            break  # Only need to check once per exercise
        
        # Step 6: Check recent performance (within 48 hours)
        if user_workout_history and "last_performed" in user_workout_history:
            last_performed_dict = user_workout_history["last_performed"]
            cutoff_time = datetime.now() - timedelta(hours=48)
            
            for exercise in available_exercises:
                if exercise.id in last_performed_dict:
                    last_performed = last_performed_dict[exercise.id]
                    if isinstance(last_performed, str):
                        # Parse ISO format string
                        try:
                            last_performed = datetime.fromisoformat(last_performed.replace('Z', '+00:00'))
                        except (ValueError, AttributeError):
                            continue
                    
                    if isinstance(last_performed, datetime):
                        days_ago = (datetime.now() - last_performed.replace(tzinfo=None)).days
                        if days_ago < 2:  # Within 48 hours
                            if exercise.id not in recommended_exercise_ids:
                                not_recommended.append(
                                    NotRecommendedExercise(
                                        exercise_id=exercise.id,
                                        exercise_name=exercise.name,
                                        reason=f"Performed {days_ago} day{'s' if days_ago != 1 else ''} ago - insufficient recovery"
                                    )
                                )
        
        # Step 7: Limit not_recommended to ~10 entries with diverse reasons
        # Group by reason type and prioritize diversity
        reason_types = {}
        for entry in not_recommended:
            reason_type = entry.reason.split(':')[0] if ':' in entry.reason else entry.reason.split(' ')[0]
            if reason_type not in reason_types:
                reason_types[reason_type] = []
            reason_types[reason_type].append(entry)
        
        # Select diverse entries (max 2-3 per reason type, up to 10 total)
        diverse_not_recommended = []
        max_per_type = 3
        for reason_type, entries in reason_types.items():
            diverse_not_recommended.extend(entries[:max_per_type])
            if len(diverse_not_recommended) >= 10:
                break
        
        not_recommended = diverse_not_recommended[:10]
        
        # Step 8: Now work with available exercises for recommendations
        exercises = available_exercises
        filtered_by_equipment = filtered_by_equipment_count
        
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
        
        # Mark recommended exercises to avoid duplicates in not_recommended
        for rec in recommendations:
            recommended_exercise_ids.add(rec.exercise_id)
        
        # Filter out any not_recommended entries that are actually recommended
        not_recommended = [
            entry for entry in not_recommended
            if entry.exercise_id not in recommended_exercise_ids
        ]
        
        return RecommendationResponse(
            recommendations=recommendations,
            not_recommended=not_recommended,
            total_candidates=total_candidates,
            filtered_by_equipment=filtered_by_equipment,
            provider="fallback",
        )
