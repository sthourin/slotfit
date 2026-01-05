"""
Slot Template model - reusable slot configurations
"""
from sqlalchemy import Column, String, Integer, Text, Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
import enum

from app.models.base import Base


class SlotType(str, enum.Enum):
    """Slot type enumeration"""
    STANDARD = "standard"
    WARMUP = "warmup"
    FINISHER = "finisher"
    ACTIVE_RECOVERY = "active_recovery"
    WILDCARD = "wildcard"


class SlotTemplate(Base):
    __tablename__ = "slot_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    slot_type = Column(SQLEnum(SlotType, values_callable=lambda x: [e.value for e in x]), default=SlotType.STANDARD, nullable=False)
    muscle_group_ids = Column(JSONB, nullable=False)  # Array of muscle group IDs
    
    # Optional constraints and targets
    time_limit_seconds = Column(Integer, nullable=True)
    default_exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=True)
    target_sets = Column(Integer, nullable=True)
    target_reps_min = Column(Integer, nullable=True)
    target_reps_max = Column(Integer, nullable=True)
    target_weight = Column(Float, nullable=True)
    target_rest_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Note: user_id deferred to future phase (MVP is offline-only)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<SlotTemplate(id={self.id}, name='{self.name}', slot_type='{self.slot_type.value}')>"
