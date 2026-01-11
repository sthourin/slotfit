"""
Pydantic schemas for Workout API
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.workout import WorkoutState, SlotState


class WorkoutSetBase(BaseModel):
    set_number: int
    reps: Optional[int] = None
    weight: Optional[float] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None


class WorkoutSetCreate(WorkoutSetBase):
    pass


class WorkoutSetUpdate(BaseModel):
    reps: Optional[int] = None
    weight: Optional[float] = None
    rest_seconds: Optional[int] = None
    notes: Optional[str] = None


class WorkoutSetResponse(WorkoutSetBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    workout_exercise_id: int


class WorkoutExerciseBase(BaseModel):
    exercise_id: int
    slot_id: Optional[int] = None
    slot_state: SlotState = SlotState.NOT_STARTED
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class WorkoutExerciseCreate(WorkoutExerciseBase):
    pass


class WorkoutExerciseUpdate(BaseModel):
    slot_state: Optional[SlotState] = None
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


class WorkoutExerciseResponse(WorkoutExerciseBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    workout_session_id: int
    sets: List[WorkoutSetResponse] = []
    routine_slot_id: Optional[int] = None  # Alias for slot_id for API clarity
    
    @model_validator(mode='after')
    def set_routine_slot_id(self):
        """Set routine_slot_id from slot_id if not already set"""
        if self.routine_slot_id is None:
            self.routine_slot_id = self.slot_id
        return self


class WorkoutSessionBase(BaseModel):
    routine_template_id: Optional[int] = None
    state: WorkoutState = WorkoutState.DRAFT


class WorkoutSessionCreate(WorkoutSessionBase):
    pass


class WorkoutSessionUpdate(BaseModel):
    routine_template_id: Optional[int] = None
    state: Optional[WorkoutState] = None


class WorkoutSessionResponse(WorkoutSessionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exercises: List[WorkoutExerciseResponse] = []


class WorkoutSessionListResponse(BaseModel):
    workouts: List[WorkoutSessionResponse]
    total: int


class AddExerciseToWorkoutRequest(BaseModel):
    """Request schema for adding an exercise to a workout slot"""
    routine_slot_id: int  # The routine slot ID (maps to slot_id in WorkoutExercise)
    exercise_id: int
