"""
Workout Session, Exercise, Set, and Heart Rate models
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Float,
    Enum as SQLEnum,
    Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import Base


class WorkoutState(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SlotState(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class HeartRateZone(str, enum.Enum):
    FAT_BURN = "fat_burn"  # 50-60% max HR
    CARDIO = "cardio"  # 60-70% max HR
    PEAK = "peak"  # 70-85% max HR
    MAXIMUM = "maximum"  # 85-100% max HR


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True, index=True)
    routine_template_id = Column(Integer, ForeignKey("routine_templates.id"), nullable=True)
    
    # Workout state
    state = Column(SQLEnum(WorkoutState), default=WorkoutState.DRAFT, nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    routine_template = relationship("RoutineTemplate")
    user = relationship("User", backref="workout_sessions")
    exercises = relationship(
        "WorkoutExercise",
        back_populates="workout_session",
        order_by="WorkoutExercise.started_at",
        cascade="all, delete-orphan",
    )
    heart_rate_analytics = relationship(
        "HeartRateAnalytics",
        back_populates="workout_session",
        cascade="all, delete-orphan",
    )
    tags = relationship(
        "Tag",
        secondary="workout_session_tags",
        back_populates="workout_sessions",
    )

    def __repr__(self):
        return f"<WorkoutSession(id={self.id}, state='{self.state}')>"


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, index=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("routine_slots.id"), nullable=True)  # Can be null if slot deleted
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    
    # Slot state
    slot_state = Column(SQLEnum(SlotState), default=SlotState.NOT_STARTED, nullable=False)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)

    # Relationships
    workout_session = relationship("WorkoutSession", back_populates="exercises")
    slot = relationship("RoutineSlot", back_populates="workout_exercises")
    exercise = relationship("Exercise")
    sets = relationship(
        "WorkoutSet",
        back_populates="workout_exercise",
        order_by="WorkoutSet.set_number",
        cascade="all, delete-orphan",
    )
    heart_rate_readings = relationship(
        "HeartRateReading",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
    )
    heart_rate_analytics = relationship(
        "HeartRateAnalytics",
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<WorkoutExercise(id={self.id}, exercise_id={self.exercise_id})>"


class WorkoutSet(Base):
    __tablename__ = "workout_sets"

    id = Column(Integer, primary_key=True, index=True)
    workout_exercise_id = Column(Integer, ForeignKey("workout_exercises.id"), nullable=False)
    set_number = Column(Integer, nullable=False)
    reps = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)  # In user's preferred units
    rest_seconds = Column(Integer, nullable=True)
    rpe = Column(Float, nullable=True)  # Rate of Perceived Exertion (1-10 scale)
    notes = Column(Text, nullable=True)

    # Relationships
    workout_exercise = relationship("WorkoutExercise", back_populates="sets")

    def __repr__(self):
        return f"<WorkoutSet(id={self.id}, set_number={self.set_number}, reps={self.reps})>"


class HeartRateReading(Base):
    __tablename__ = "heart_rate_readings"

    id = Column(Integer, primary_key=True, index=True)
    workout_exercise_id = Column(Integer, ForeignKey("workout_exercises.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    bpm = Column(Integer, nullable=False)
    zone = Column(SQLEnum(HeartRateZone), nullable=True)

    # Relationships
    workout_exercise = relationship("WorkoutExercise", back_populates="heart_rate_readings")

    def __repr__(self):
        return f"<HeartRateReading(id={self.id}, bpm={self.bpm}, timestamp={self.timestamp})>"


class HeartRateAnalytics(Base):
    __tablename__ = "heart_rate_analytics"

    id = Column(Integer, primary_key=True, index=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=True)
    workout_exercise_id = Column(Integer, ForeignKey("workout_exercises.id"), nullable=True)
    slot_id = Column(Integer, ForeignKey("routine_slots.id"), nullable=True)
    
    # Level: "exercise", "slot", or "workout"
    level = Column(String, nullable=False, index=True)
    
    # Metrics
    avg_hr = Column(Float, nullable=True)
    peak_hr = Column(Integer, nullable=True)
    min_hr = Column(Integer, nullable=True)
    
    # Zone metrics (time in seconds)
    time_in_fat_burn = Column(Integer, default=0)
    time_in_cardio = Column(Integer, default=0)
    time_in_peak = Column(Integer, default=0)
    time_in_maximum = Column(Integer, default=0)
    
    # Zone distribution (percentages)
    fat_burn_percentage = Column(Float, default=0.0)
    cardio_percentage = Column(Float, default=0.0)
    peak_percentage = Column(Float, default=0.0)
    maximum_percentage = Column(Float, default=0.0)
    
    # Trend
    trend = Column(String, nullable=True)  # "rising", "falling", "stable"

    # Relationships
    workout_session = relationship("WorkoutSession", back_populates="heart_rate_analytics")
    workout_exercise = relationship("WorkoutExercise", back_populates="heart_rate_analytics")

    def __repr__(self):
        return f"<HeartRateAnalytics(id={self.id}, level='{self.level}', avg_hr={self.avg_hr})>"
