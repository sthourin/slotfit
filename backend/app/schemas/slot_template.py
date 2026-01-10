"""
Pydantic schemas for Slot Template API
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, field_validator, model_validator, ConfigDict

from app.models.slot_template import SlotType


class SlotTemplateBase(BaseModel):
    name: str
    slot_type: SlotType = SlotType.STANDARD
    muscle_group_ids: List[int]
    time_limit_seconds: Optional[int] = None
    default_exercise_id: Optional[int] = None
    target_sets: Optional[int] = None
    target_reps_min: Optional[int] = None
    target_reps_max: Optional[int] = None
    target_weight: Optional[float] = None
    target_rest_seconds: Optional[int] = None
    notes: Optional[str] = None

    @field_validator('muscle_group_ids')
    @classmethod
    def validate_muscle_group_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('muscle_group_ids must contain at least one muscle group ID')
        return v

    @model_validator(mode='after')
    def validate_rep_range(self):
        if self.target_reps_min is not None and self.target_reps_max is not None:
            if self.target_reps_min > self.target_reps_max:
                raise ValueError('target_reps_min must be less than or equal to target_reps_max')
        return self


class SlotTemplateCreate(SlotTemplateBase):
    pass


class SlotTemplateUpdate(BaseModel):
    name: Optional[str] = None
    slot_type: Optional[SlotType] = None
    muscle_group_ids: Optional[List[int]] = None
    time_limit_seconds: Optional[int] = None
    default_exercise_id: Optional[int] = None
    target_sets: Optional[int] = None
    target_reps_min: Optional[int] = None
    target_reps_max: Optional[int] = None
    target_weight: Optional[float] = None
    target_rest_seconds: Optional[int] = None
    notes: Optional[str] = None


class SlotTemplateResponse(SlotTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
