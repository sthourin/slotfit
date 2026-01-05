"""
Equipment schemas
"""
from pydantic import BaseModel
from typing import Optional


class EquipmentBase(BaseModel):
    name: str
    category: Optional[str] = None


class EquipmentResponse(EquipmentBase):
    id: int
    exercise_count: int = 0  # Number of exercises using this equipment
    
    class Config:
        from_attributes = True


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
