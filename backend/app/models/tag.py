"""
Tag model for exercises, routines, and workouts
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.base import Base


# Junction tables for many-to-many relationships
exercise_tags = Table(
    "exercise_tags",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

routine_template_tags = Table(
    "routine_template_tags",
    Base.metadata,
    Column("routine_template_id", Integer, ForeignKey("routine_templates.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

workout_session_tags = Table(
    "workout_session_tags",
    Base.metadata,
    Column("workout_session_id", Integer, ForeignKey("workout_sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    # Optional: category to group tags (e.g., "classification", "style", "type")
    category = Column(String, nullable=True, index=True)

    # Relationships
    exercises = relationship(
        "Exercise",
        secondary=exercise_tags,
        back_populates="tags",
    )
    routine_templates = relationship(
        "RoutineTemplate",
        secondary=routine_template_tags,
        back_populates="tags",
    )
    workout_sessions = relationship(
        "WorkoutSession",
        secondary=workout_session_tags,
        back_populates="tags",
    )

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"
