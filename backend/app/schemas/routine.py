"""
Pydantic schemas for Routine API
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, model_validator

from app.models.slot_template import SlotType


class RoutineSlotBase(BaseModel):
    name: Optional[str] = None  # Optional name for the slot
    order: int
    muscle_group_ids: List[int] = []  # Allow empty list
    superset_tag: Optional[str] = None
    selected_exercise_id: Optional[int] = None  # Optional pre-selected exercise
    workout_style: Optional[str] = None  # Optional workout style for this slot (overrides routine workout_style)
    
    # New enhanced fields
    slot_type: SlotType = SlotType.STANDARD
    slot_template_id: Optional[int] = None  # Optional reference to slot template
    time_limit_seconds: Optional[int] = None  # Optional time cap for the slot
    required_equipment_ids: Optional[List[int]] = None  # Array of equipment IDs - conditional visibility
    target_sets: Optional[int] = None  # Target number of sets
    target_reps_min: Optional[int] = None  # Target rep range minimum
    target_reps_max: Optional[int] = None  # Target rep range maximum
    target_weight: Optional[float] = None  # Target weight
    target_time_seconds: Optional[int] = None  # Target time (for time-based exercises)
    target_rest_seconds: Optional[int] = None  # Target rest period
    progression_rule: Optional[Dict[str, Any]] = None  # Auto-progression configuration

    @model_validator(mode='after')
    def validate_rep_range(self):
        if self.target_reps_min is not None and self.target_reps_max is not None:
            if self.target_reps_min > self.target_reps_max:
                raise ValueError('target_reps_min must be less than or equal to target_reps_max')
        return self


class RoutineSlotCreate(RoutineSlotBase):
    pass


class RoutineSlotResponse(RoutineSlotBase):
    id: int
    routine_template_id: int

    class Config:
        from_attributes = True


class RoutineTemplateBase(BaseModel):
    name: str
    routine_type: Optional[str] = None
    workout_style: Optional[str] = None
    description: Optional[str] = None


class RoutineTemplateCreate(RoutineTemplateBase):
    slots: List[RoutineSlotCreate] = []


class RoutineTemplateUpdate(BaseModel):
    name: Optional[str] = None
    routine_type: Optional[str] = None
    workout_style: Optional[str] = None
    description: Optional[str] = None


class RoutineTemplateResponse(RoutineTemplateBase):
    id: int
    slots: List[RoutineSlotResponse] = []

    class Config:
        from_attributes = True


class RoutineTemplateListResponse(BaseModel):
    routines: List[RoutineTemplateResponse]
    total: int
