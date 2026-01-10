"""
SQLAlchemy database models
"""
from app.models.base import Base
from app.models.muscle_group import MuscleGroup
from app.models.equipment import Equipment
from app.models.exercise import Exercise
from app.models.routine import RoutineTemplate, RoutineSlot
from app.models.workout import (
    WorkoutSession,
    WorkoutExercise,
    WorkoutSet,
    HeartRateReading,
    HeartRateAnalytics,
)
from app.models.equipment_profile import EquipmentProfile
from app.models.slot_template import SlotTemplate, SlotType
from app.models.personal_record import PersonalRecord, RecordType
from app.models.weekly_volume import WeeklyVolume
from app.models.injury import InjuryType, MovementRestriction, UserInjury
from app.models.user import User

__all__ = [
    "Base",
    "MuscleGroup",
    "Equipment",
    "Exercise",
    "RoutineTemplate",
    "RoutineSlot",
    "WorkoutSession",
    "WorkoutExercise",
    "WorkoutSet",
    "HeartRateReading",
    "HeartRateAnalytics",
    "EquipmentProfile",
    "SlotTemplate",
    "SlotType",
    "PersonalRecord",
    "RecordType",
    "WeeklyVolume",
    "InjuryType",
    "MovementRestriction",
    "UserInjury",
    "User",
]
