"""Pydantic schemas for movement patterns"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PatternResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    opposite_pattern_id: Optional[int]
    is_neutral: bool
    display_order: int


class TrendPoint(BaseModel):
    week_start: date
    index: float


class PatternProgressResponse(BaseModel):
    pattern_id: int
    slug: str
    name: str
    trend: List[TrendPoint]
