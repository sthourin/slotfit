"""
Pydantic schemas for Workout API
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

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
    id: int
    workout_exercise_id: int

    class Config:
        from_attributes = True


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
    id: int
    workout_session_id: int
    sets: List[WorkoutSetResponse] = []

    class Config:
        from_attributes = True


class WorkoutSessionBase(BaseModel):
    routine_template_id: Optional[int] = None
    state: WorkoutState = WorkoutState.DRAFT


class WorkoutSessionCreate(WorkoutSessionBase):
    pass


class WorkoutSessionUpdate(BaseModel):
    routine_template_id: Optional[int] = None
    state: Optional[WorkoutState] = None


class WorkoutSessionResponse(WorkoutSessionBase):
    id: int
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exercises: List[WorkoutExerciseResponse] = []

    class Config:
        from_attributes = True


class WorkoutSessionListResponse(BaseModel):
    workouts: List[WorkoutSessionResponse]
    total: int
