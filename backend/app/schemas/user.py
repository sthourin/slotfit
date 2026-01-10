"""
Pydantic schemas for User API
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    device_id: Optional[str]
    display_name: str
    preferred_units: str
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    preferred_units: Optional[str] = None  # "lbs" or "kg"
