"""
Pydantic schemas for Exercise API
"""
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime

from app.models.exercise import DifficultyLevel
from app.schemas.tag import Tag


class MuscleGroupBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    level: int
    parent_id: Optional[int] = None


class EquipmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    category: Optional[str] = None


class ExerciseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    exercise_classification: Optional[str] = None
    short_demo_url: Optional[str] = None
    in_depth_url: Optional[str] = None


class Exercise(ExerciseBase):
    primary_equipment: Optional[EquipmentBase] = None
    secondary_equipment: Optional[EquipmentBase] = None
    primary_equipment_count: int = 1
    secondary_equipment_count: int = 0
    muscle_groups: List[MuscleGroupBase] = []
    posture: Optional[str] = None
    movement_pattern_1: Optional[str] = None
    movement_pattern_2: Optional[str] = None
    movement_pattern_3: Optional[str] = None
    body_region: Optional[str] = None
    force_type: Optional[str] = None
    mechanics: Optional[str] = None
    laterality: Optional[str] = None
    last_performed: Optional[datetime] = None  # Calculated from workout history
    # Variant fields
    base_exercise_id: Optional[int] = None
    variant_type: Optional[str] = None  # "HIIT", "Strength", "Volume", "Endurance", "Custom"
    is_custom: bool = False
    default_sets: Optional[int] = None
    default_reps: Optional[int] = None
    default_weight: Optional[float] = None
    default_time_seconds: Optional[int] = None
    default_rest_seconds: Optional[int] = None
    tags: List[Tag] = []

    model_config = ConfigDict(from_attributes=True)


class ExerciseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None


class ExerciseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None


class ExerciseDuplicate(BaseModel):
    """Schema for duplicating an exercise to create a variant"""
    name: Optional[str] = None  # If not provided, will append variant_type to original name
    variant_type: str  # "HIIT", "Strength", "Volume", "Endurance", "Custom"
    default_sets: Optional[int] = None
    default_reps: Optional[int] = None
    default_weight: Optional[float] = None
    default_time_seconds: Optional[int] = None
    default_rest_seconds: Optional[int] = None


class ExerciseListResponse(BaseModel):
    exercises: List[Exercise]
    total: int
    page: int
    page_size: int
