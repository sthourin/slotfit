"""
Analytics service - business logic for analytics endpoints
"""
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from sqlalchemy.orm import selectinload

from app.models import (
    MuscleGroup,
    WorkoutSession,
    WorkoutExercise,
    WorkoutSet,
    RoutineSlot,
    RoutineTemplate,
    PersonalRecord,
    Exercise,
)
from app.services.bodyweight_service import (
    bodyweight_timeline,
    effective_load,
    resolve_bodyweight,
)
from app.services.exercise_helpers import bodyweight_equipment_id
from app.services.volume_service import weekly_volume_by_muscle_group


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_weekly_volume(self, week_start: date, user_id: int) -> Dict[str, Any]:
        """
        Get weekly volume data for all muscle groups for a given week
        
        Args:
            week_start: Monday date of the week (ISO week start)
            user_id: ID of the user
            
        Returns:
            Dict with week_start and muscle_groups array

        Computed live from logged sets. This used to read the `weekly_volume`
        aggregate table, which nothing has ever written, so every figure the
        chart showed was zero no matter how much training was logged.
        """
        totals = await weekly_volume_by_muscle_group(self.db, user_id, week_start)
        if not totals:
            return {"week_start": week_start.isoformat(), "muscle_groups": []}

        names = dict(
            (
                await self.db.execute(
                    select(MuscleGroup.id, MuscleGroup.name).where(
                        MuscleGroup.id.in_(totals.keys())
                    )
                )
            ).all()
        )

        muscle_groups = [
            {
                "muscle_group_id": muscle_group_id,
                "name": names.get(muscle_group_id, str(muscle_group_id)),
                "total_sets": bucket["total_sets"],
                "total_reps": bucket["total_reps"],
                "total_volume": round(bucket["total_volume"], 2),
            }
            for muscle_group_id, bucket in totals.items()
        ]
        muscle_groups.sort(key=lambda entry: entry["name"])

        return {
            "week_start": week_start.isoformat(),
            "muscle_groups": muscle_groups,
        }

    async def get_slot_performance(self, routine_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get performance metrics for slots in a routine
        
        Args:
            routine_id: ID of the routine template
            user_id: ID of the user
            
        Returns:
            Dict with routine info and slot performance metrics
        """
        # Get routine template
        routine_query = select(RoutineTemplate).where(
            and_(
                RoutineTemplate.id == routine_id,
                RoutineTemplate.user_id == user_id
            )
        )
        routine_result = await self.db.execute(routine_query)
        routine = routine_result.scalar_one_or_none()
        
        if not routine:
            raise ValueError(f"Routine {routine_id} not found")
        
        # Get all slots for the routine
        slots_query = select(RoutineSlot).where(
            RoutineSlot.routine_template_id == routine_id
        ).order_by(RoutineSlot.order)
        
        slots_result = await self.db.execute(slots_query)
        slots = slots_result.scalars().all()
        
        slot_performance = []
        for slot in slots:
            # Get workout exercises for this slot (only from user's workouts)
            exercises_query = (
                select(WorkoutExercise)
                .join(WorkoutSession, WorkoutExercise.workout_session_id == WorkoutSession.id)
                .where(
                    and_(
                        WorkoutExercise.slot_id == slot.id,
                        WorkoutSession.user_id == user_id
                    )
                )
                .options(selectinload(WorkoutExercise.sets))
            )
            
            exercises_result = await self.db.execute(exercises_query)
            workout_exercises = exercises_result.scalars().all()
            
            # Calculate metrics
            total_workouts = len(set(we.workout_session_id for we in workout_exercises))
            completed_count = sum(1 for we in workout_exercises if we.slot_state.value == "completed")
            skipped_count = sum(1 for we in workout_exercises if we.slot_state.value == "skipped")
            
            # Get average sets per workout
            total_sets = 0
            for we in workout_exercises:
                if we.sets:
                    total_sets += len(we.sets)
            
            avg_sets = total_sets / total_workouts if total_workouts > 0 else 0
            
            # Get most used exercise
            exercise_counts = {}
            for we in workout_exercises:
                exercise_counts[we.exercise_id] = exercise_counts.get(we.exercise_id, 0) + 1
            
            most_used_exercise_id = max(exercise_counts.items(), key=lambda x: x[1])[0] if exercise_counts else None
            
            slot_performance.append({
                "slot_id": slot.id,
                "slot_name": slot.name,
                "slot_order": slot.order,
                "total_workouts": total_workouts,
                "completed_count": completed_count,
                "skipped_count": skipped_count,
                "completion_rate": (completed_count / total_workouts * 100) if total_workouts > 0 else 0,
                "avg_sets_per_workout": round(avg_sets, 2),
                "most_used_exercise_id": most_used_exercise_id,
            })
        
        return {
            "routine_id": routine_id,
            "routine_name": routine.name,
            "slots": slot_performance,
        }

    async def get_exercise_progression(self, exercise_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get progression data for a specific exercise
        
        Args:
            exercise_id: ID of the exercise
            user_id: ID of the user
            
        Returns:
            Dict with exercise info and progression data
        """
        # Verify exercise exists
        exercise_query = select(Exercise).where(Exercise.id == exercise_id)
        exercise_result = await self.db.execute(exercise_query)
        exercise = exercise_result.scalar_one_or_none()
        
        if not exercise:
            raise ValueError(f"Exercise {exercise_id} not found")
        
        # Get personal records for this exercise (only for this user)
        prs_query = select(PersonalRecord).where(
            and_(
                PersonalRecord.exercise_id == exercise_id,
                PersonalRecord.user_id == user_id
            )
        ).order_by(PersonalRecord.achieved_at)
        
        prs_result = await self.db.execute(prs_query)
        prs = prs_result.scalars().all()
        
        # Group PRs by type
        prs_by_type = {}
        for pr in prs:
            if pr.record_type.value not in prs_by_type:
                prs_by_type[pr.record_type.value] = []
            prs_by_type[pr.record_type.value].append({
                "value": pr.value,
                "achieved_at": pr.achieved_at.isoformat(),
                "context": pr.context,
            })
        
        # Get workout history (recent workouts with this exercise, only for this user)
        workouts_query = (
            select(WorkoutExercise, WorkoutSession.completed_at)
            .join(WorkoutSession, WorkoutExercise.workout_session_id == WorkoutSession.id)
            .where(
                and_(
                    WorkoutExercise.exercise_id == exercise_id,
                    WorkoutSession.completed_at.isnot(None),
                    WorkoutSession.user_id == user_id
                )
            )
            .order_by(desc(WorkoutSession.completed_at))
            .limit(10)
        )
        
        workouts_result = await self.db.execute(workouts_query)
        workout_rows = workouts_result.all()

        # Fetched once, not per set. Bodyweight work carries real load, and
        # counting it as zero tonnage understated whole sessions of push-ups
        # and squats; each set is scored against the reading in effect on the
        # day it was performed.
        timeline = await bodyweight_timeline(self.db, user_id)
        bodyweight_id = await bodyweight_equipment_id(self.db)

        recent_workouts = []
        for we, completed_at in workout_rows:
            # Get sets for this workout exercise
            sets_query = select(WorkoutSet).where(
                WorkoutSet.workout_exercise_id == we.id
            ).order_by(WorkoutSet.set_number)
            
            sets_result = await self.db.execute(sets_query)
            sets = sets_result.scalars().all()
            
            bodyweight = resolve_bodyweight(timeline, completed_at) if completed_at else None
            total_volume = sum(
                (effective_load(exercise, s.weight, bodyweight, bodyweight_id) or 0)
                * (s.reps or 0)
                for s in sets
            )
            # avg_weight stays the LOGGED weight: it is what the user typed, and
            # silently reporting a leverage-derived number under that name would
            # misrepresent their own history back to them.
            avg_weight = sum(s.weight or 0 for s in sets) / len(sets) if sets else 0
            avg_reps = sum(s.reps or 0 for s in sets) / len(sets) if sets else 0
            
            recent_workouts.append({
                "workout_session_id": we.workout_session_id,
                "completed_at": completed_at.isoformat() if completed_at else None,
                "sets_count": len(sets),
                "total_volume": total_volume,
                "avg_weight": round(avg_weight, 2),
                "avg_reps": round(avg_reps, 2),
            })
        
        return {
            "exercise_id": exercise_id,
            "exercise_name": exercise.name,
            "personal_records": prs_by_type,
            "recent_workouts": recent_workouts,
        }
