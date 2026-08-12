"""Pydantic schemas for anchor/partner suggestions"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

from app.schemas.training_session import TargetResponse


class PatternInfo(BaseModel):
    id: int
    slug: str
    name: str


class SuggestionCard(BaseModel):
    exercise_id: int
    exercise_name: str
    pattern_id: int
    pattern_slug: str
    equipment_name: Optional[str]
    is_bodyweight: bool
    last_performed: Optional[datetime]
    is_staple: bool
    target: Optional[TargetResponse]


class NotRecommendedEntry(BaseModel):
    exercise_name: str
    reason: str


class AnchorGroup(BaseModel):
    pattern: PatternInfo
    covered: bool
    staples: List[SuggestionCard]


class AnchorSuggestionsResponse(BaseModel):
    groups: List[AnchorGroup]
    # Patterns the day plan does not ask for, offered below the plan's own
    # groups so a taken station never blocks the session.
    other_groups: List[AnchorGroup] = []
    not_recommended: List[NotRecommendedEntry]


class PartnerSuggestionsResponse(BaseModel):
    candidates: List[SuggestionCard]
    novelty: Optional[SuggestionCard]
    not_recommended: List[NotRecommendedEntry]
