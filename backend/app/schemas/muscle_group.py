"""
Pydantic schemas for Muscle Group API
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class MuscleGroupBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    level: int
    parent_id: Optional[int] = None


class MuscleGroupListResponse(BaseModel):
    muscle_groups: List[MuscleGroupBase]
