"""
Movement pattern taxonomy models
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class MovementPattern(Base):
    """Curated training pattern (~10 rows, seeded)."""
    __tablename__ = "movement_patterns"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    opposite_pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=True)
    is_neutral = Column(Boolean, default=False, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)

    opposite = relationship("MovementPattern", remote_side=[id], uselist=False)

    def __repr__(self):
        return f"<MovementPattern(id={self.id}, slug='{self.slug}')>"


class ExercisePatternMap(Base):
    """Maps each exercise to exactly one curated pattern."""
    __tablename__ = "exercise_pattern_map"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), unique=True, nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False, index=True)
    is_override = Column(Boolean, default=False, nullable=False)

    exercise = relationship("Exercise")
    pattern = relationship("MovementPattern")

    def __repr__(self):
        return f"<ExercisePatternMap(exercise_id={self.exercise_id}, pattern_id={self.pattern_id})>"
