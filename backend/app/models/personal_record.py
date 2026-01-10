"""
Personal Record model - tracks PRs per exercise variant
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.models.base import Base


class RecordType(str, enum.Enum):
    """Record type enumeration"""
    WEIGHT = "weight"
    REPS = "reps"
    VOLUME = "volume"
    TIME = "time"


class PersonalRecord(Base):
    __tablename__ = "personal_records"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    record_type = Column(SQLEnum(RecordType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    value = Column(Float, nullable=False)
    context = Column(JSONB, nullable=True)  # Additional context (e.g., {"reps": 8} for weight PR, {"weight": 135} for rep PR)
    achieved_at = Column(DateTime(timezone=True), nullable=False, index=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    exercise = relationship("Exercise", foreign_keys=[exercise_id])
    workout_session = relationship("WorkoutSession", foreign_keys=[workout_session_id])
    user = relationship("User", backref="personal_records")

    def __repr__(self):
        return f"<PersonalRecord(id={self.id}, exercise_id={self.exercise_id}, record_type='{self.record_type}', value={self.value})>"
