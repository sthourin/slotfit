"""Pydantic schemas for training sessions"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class EntrySetCreate(BaseModel):
    set_number: int = Field(..., ge=1, le=50)
    weight: Optional[float] = Field(None, ge=0)
    reps: Optional[int] = Field(None, ge=0, le=500)
    time_seconds: Optional[int] = Field(None, ge=0)
    completed: bool = True


class EntrySetResponse(EntrySetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entry_id: int


class RoundEntryCreate(BaseModel):
    exercise_id: int
    position: int = Field(..., ge=1, le=3)


class TargetResponse(BaseModel):
    weight: Optional[float]
    # None for time-only work, which gets no rep prescription at all.
    reps: Optional[int] = None
    sets: int
    time_seconds: Optional[int] = None
    # "target" = do exactly this many reps; "beat" = exceed this many (AMRAP);
    # None = no rep prescription.
    reps_goal: Optional[str] = None
    last_summary: Optional[str]  # e.g. "3x10 @ 120", "2x300s"


class RoundEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    round_id: int
    position: int
    exercise_id: int
    exercise_name: str
    pattern_id: int
    pattern_slug: str
    set_protocol: str
    # The web card labels the weight input "+ weight" for bodyweight movements,
    # and nothing else on this response exposes equipment.
    is_bodyweight: bool = False
    default_time_seconds: Optional[int] = None
    sets: List[EntrySetResponse] = []
    target: Optional[TargetResponse] = None


class SupersetRoundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    order: int
    entries: List[RoundEntryResponse] = []


class TrainingSessionCreate(BaseModel):
    day_plan_id: Optional[int] = None


class TrainingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_plan_id: Optional[int]
    state: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    rounds: List[SupersetRoundResponse] = []


class CoverageGoal(BaseModel):
    pattern_id: int
    slug: str
    name: str
    required: bool
    target_sets: int
    sets_done: int
    covered: bool


class CoverageResponse(BaseModel):
    goals: List[CoverageGoal]
