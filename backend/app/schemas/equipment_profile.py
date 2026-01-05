"""
Pydantic schemas for Equipment Profile API
"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class EquipmentProfileBase(BaseModel):
    name: str
    equipment_ids: List[int]
    is_default: Optional[bool] = False


class EquipmentProfileCreate(EquipmentProfileBase):
    pass


class EquipmentProfileUpdate(BaseModel):
    name: Optional[str] = None
    equipment_ids: Optional[List[int]] = None
    is_default: Optional[bool] = None


class EquipmentProfileResponse(EquipmentProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
