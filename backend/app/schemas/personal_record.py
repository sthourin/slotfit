"""
Pydantic schemas for Personal Record API
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict

from app.models.personal_record import RecordType


class PersonalRecordBase(BaseModel):
    exercise_id: int
    record_type: RecordType
    value: float
    context: Optional[Dict[str, Any]] = None
    achieved_at: datetime
    workout_session_id: Optional[int] = None

    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        if v <= 0:
            raise ValueError('value must be greater than 0')
        return v


class PersonalRecordCreate(PersonalRecordBase):
    pass


class PersonalRecordUpdate(BaseModel):
    exercise_id: Optional[int] = None
    record_type: Optional[RecordType] = None
    value: Optional[float] = None
    context: Optional[Dict[str, Any]] = None
    achieved_at: Optional[datetime] = None
    workout_session_id: Optional[int] = None


class PersonalRecordResponse(PersonalRecordBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int


class PersonalRecordListResponse(BaseModel):
    """Response for listing personal records"""
    records: list[PersonalRecordResponse]
    total: int
