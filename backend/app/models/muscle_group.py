"""
Muscle Group model - hierarchical structure
Level 1: Target Muscle Group (e.g., "Abdominals", "Back")
Level 2: Prime Mover Muscle (e.g., "Rectus Abdominis")
Level 3: Secondary Muscle
Level 4: Tertiary Muscle
"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class MuscleGroup(Base):
    __tablename__ = "muscle_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=True)
    level = Column(Integer, nullable=False)  # 1=Target, 2=Prime, 3=Secondary, 4=Tertiary

    # Relationships
    parent = relationship("MuscleGroup", remote_side=[id], backref="children")
    exercises = relationship(
        "Exercise",
        secondary="exercise_muscle_groups",
        back_populates="muscle_groups",
    )

    def __repr__(self):
        return f"<MuscleGroup(id={self.id}, name='{self.name}', level={self.level})>"
