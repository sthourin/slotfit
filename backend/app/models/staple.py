"""
Staple exercises (per-pattern proven pool) and exercise preferences (blacklist)
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class StapleExercise(Base):
    __tablename__ = "staple_exercises"
    __table_args__ = (UniqueConstraint("user_id", "exercise_id", name="uq_staple_user_exercise"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    pattern = relationship("MovementPattern")
    exercise = relationship("Exercise")

    def __repr__(self):
        return f"<StapleExercise(user_id={self.user_id}, exercise_id={self.exercise_id})>"


class ExercisePreference(Base):
    __tablename__ = "exercise_preferences"
    __table_args__ = (UniqueConstraint("user_id", "exercise_id", name="uq_pref_user_exercise"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    preference = Column(String, nullable=False, default="never")  # only "never" for now

    exercise = relationship("Exercise")

    def __repr__(self):
        return f"<ExercisePreference(user_id={self.user_id}, exercise_id={self.exercise_id}, preference='{self.preference}')>"
