"""
Equipment model - extracted from exercise database CSV
"""
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from app.models.base import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, nullable=True)  # e.g., "Free Weights", "Machines", "Bodyweight"

    # Relationships
    primary_exercises = relationship(
        "Exercise", foreign_keys="Exercise.primary_equipment_id", back_populates="primary_equipment"
    )
    secondary_exercises = relationship(
        "Exercise", foreign_keys="Exercise.secondary_equipment_id", back_populates="secondary_equipment"
    )

    def __repr__(self):
        return f"<Equipment(id={self.id}, name='{self.name}')>"
