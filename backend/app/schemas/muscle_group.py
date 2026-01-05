"""
Pydantic schemas for Muscle Group API
"""
from typing import Optional, List
from pydantic import BaseModel


class MuscleGroupBase(BaseModel):
    id: int
    name: str
    level: int
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class MuscleGroupListResponse(BaseModel):
    muscle_groups: List[MuscleGroupBase]
