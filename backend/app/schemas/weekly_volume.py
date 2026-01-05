"""
Pydantic schemas for Weekly Volume API
"""
from typing import Optional
from datetime import date
from pydantic import BaseModel, field_validator


class WeeklyVolumeBase(BaseModel):
    muscle_group_id: int
    week_start: date
    total_sets: int = 0
    total_reps: int = 0
    total_volume: float = 0.0

    @field_validator('total_sets', 'total_reps')
    @classmethod
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError('total_sets and total_reps must be non-negative')
        return v

    @field_validator('total_volume')
    @classmethod
    def validate_volume(cls, v):
        if v < 0:
            raise ValueError('total_volume must be non-negative')
        return v

    @field_validator('week_start')
    @classmethod
    def validate_week_start(cls, v):
        # Ensure week_start is a Monday (ISO week start)
        # weekday() returns 0 for Monday, 6 for Sunday
        if v.weekday() != 0:
            raise ValueError('week_start must be a Monday')
        return v


class WeeklyVolumeCreate(WeeklyVolumeBase):
    pass


class WeeklyVolumeUpdate(BaseModel):
    muscle_group_id: Optional[int] = None
    week_start: Optional[date] = None
    total_sets: Optional[int] = None
    total_reps: Optional[int] = None
    total_volume: Optional[float] = None


class WeeklyVolumeResponse(WeeklyVolumeBase):
    id: int

    class Config:
        from_attributes = True


class WeeklyVolumeListResponse(BaseModel):
    """Response for listing weekly volume records"""
    records: list[WeeklyVolumeResponse]
    total: int
