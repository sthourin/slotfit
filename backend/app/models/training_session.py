"""
Training session models - live-built superset rounds
"""
import enum

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.models.base import Base


class SessionState(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCARDED = "discarded"


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day_plan_id = Column(Integer, ForeignKey("day_plans.id"), nullable=True)
    state = Column(
        SQLEnum(SessionState, values_callable=lambda x: [e.value for e in x]),
        default=SessionState.DRAFT, nullable=False,
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", backref="training_sessions")
    day_plan = relationship("DayPlan")
    rounds = relationship(
        "SupersetRound", back_populates="session",
        order_by="SupersetRound.order", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<TrainingSession(id={self.id}, state='{self.state.value}')>"


class SupersetRound(Base):
    __tablename__ = "superset_rounds"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("training_sessions.id"), nullable=False, index=True)
    order = Column(Integer, nullable=False)

    session = relationship("TrainingSession", back_populates="rounds")
    entries = relationship(
        "RoundEntry", back_populates="round",
        order_by="RoundEntry.position", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<SupersetRound(id={self.id}, order={self.order})>"


class RoundEntry(Base):
    __tablename__ = "round_entries"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("superset_rounds.id"), nullable=False, index=True)
    position = Column(Integer, nullable=False)  # 1-3
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    # Denormalized at logging time so later mapping edits don't rewrite history
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False, index=True)

    round = relationship("SupersetRound", back_populates="entries")
    exercise = relationship("Exercise")
    pattern = relationship("MovementPattern")
    sets = relationship(
        "EntrySet", back_populates="entry",
        order_by="EntrySet.set_number", cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<RoundEntry(id={self.id}, position={self.position}, exercise_id={self.exercise_id})>"


class EntrySet(Base):
    __tablename__ = "entry_sets"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(Integer, ForeignKey("round_entries.id"), nullable=False, index=True)
    set_number = Column(Integer, nullable=False)
    weight = Column(Float, nullable=True)
    reps = Column(Integer, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    completed = Column(Boolean, default=True, nullable=False)

    entry = relationship("RoundEntry", back_populates="sets")
