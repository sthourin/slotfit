"""Schemas for bodyweight readings"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BodyweightReadingCreate(BaseModel):
    weight: float = Field(gt=0, description="In the user's preferred units")
    # Defaults to now at the endpoint, so a manual entry needs only a weight.
    recorded_at: Optional[datetime] = None
    source: str = "manual"


class BodyweightReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    weight: float
    recorded_at: datetime
    source: str
