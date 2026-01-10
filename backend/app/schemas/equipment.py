"""
Equipment schemas
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class EquipmentBase(BaseModel):
    name: str
    category: Optional[str] = None


class EquipmentResponse(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    exercise_count: int = 0  # Number of exercises using this equipment


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
