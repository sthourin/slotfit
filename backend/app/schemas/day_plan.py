"""Pydantic schemas for Day Plans"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class PatternGoalCreate(BaseModel):
    pattern_id: int
    required: bool = True
    target_sets: Optional[int] = Field(None, ge=1, le=30)
    rep_range_min: Optional[int] = Field(None, ge=1, le=50)
    rep_range_max: Optional[int] = Field(None, ge=1, le=50)


class PatternGoalResponse(PatternGoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_plan_id: int


class DayPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    warmup_preferences: List[int] = []
    rounds_target: int = Field(3, ge=1, le=10)
    goals: List[PatternGoalCreate] = []


class DayPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    warmup_preferences: Optional[List[int]] = None
    rounds_target: Optional[int] = Field(None, ge=1, le=10)
    goals: Optional[List[PatternGoalCreate]] = None  # full replacement when provided


class DayPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: Optional[str]
    warmup_preferences: List[int]
    rounds_target: int
    goals: List[PatternGoalResponse]
