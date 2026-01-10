"""
Pydantic schemas for injury models
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class MovementRestrictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    restriction_type: str
    restriction_value: str
    severity_threshold: str


class InjuryTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    body_area: str
    description: Optional[str]
    severity_levels: List[str]
    restrictions: List[MovementRestrictionResponse] = []


class InjuryTypeListResponse(BaseModel):
    """Simplified response for listing (without restrictions)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    body_area: str
    description: Optional[str]


class UserInjuryCreate(BaseModel):
    injury_type_id: int
    severity: str = "moderate"  # mild, moderate, severe
    notes: Optional[str] = None


class UserInjuryUpdate(BaseModel):
    severity: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class UserInjuryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    injury_type_id: int
    injury_type: InjuryTypeListResponse
    severity: str
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
