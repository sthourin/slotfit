"""Pydantic schemas for staples and exercise preferences"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class StapleCreate(BaseModel):
    exercise_id: int
    # pattern_id is resolved server-side from ExercisePatternMap


class StapleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pattern_id: int
    exercise_id: int
    exercise_name: str
    is_active: bool
    added_at: datetime
    last_performed: Optional[datetime] = None  # derived, filled by endpoint


class PreferenceCreate(BaseModel):
    exercise_id: int
    preference: str = "never"


class PreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_id: int
    exercise_name: str
    preference: str
