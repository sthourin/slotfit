"""
Routine Template and Slot models
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base
from app.models.slot_template import SlotType


class RoutineTemplate(Base):
    __tablename__ = "routine_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    routine_type = Column(String, nullable=True)  # "anterior", "posterior", "full_body", "custom"
    workout_style = Column(String, nullable=True)  # "5x5", "HIIT", "volume", "strength", "custom"
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Relationships
    slots = relationship(
        "RoutineSlot",
        back_populates="routine_template",
        order_by="RoutineSlot.order",
        cascade="all, delete-orphan",
    )
    user = relationship("User", backref="routine_templates")
    tags = relationship(
        "Tag",
        secondary="routine_template_tags",
        back_populates="routine_templates",
    )

    def __repr__(self):
        return f"<RoutineTemplate(id={self.id}, name='{self.name}')>"


class RoutineSlot(Base):
    __tablename__ = "routine_slots"

    id = Column(Integer, primary_key=True, index=True)
    routine_template_id = Column(Integer, ForeignKey("routine_templates.id"), nullable=False)
    name = Column(String, nullable=True)  # Optional name for the slot (e.g., "Warm-up", "Main Set 1")
    order = Column(Integer, nullable=False)  # Mutable during workout
    muscle_group_ids = Column(JSONB, nullable=False)  # Array of muscle group IDs for slot scope
    # Note: JSONB stores as JSON array, e.g., [1, 2, 3]
    superset_tag = Column(String, nullable=True)  # Tag for visual grouping (slots with same tag are superset)
    selected_exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=True)  # Optional pre-selected exercise for this slot
    workout_style = Column(String, nullable=True)  # Optional workout style for this slot (overrides routine workout_style for exercise filtering)
    
    # New fields for enhanced slot functionality
    slot_type = Column(SQLEnum(SlotType, values_callable=lambda x: [e.value for e in x]), default=SlotType.STANDARD, nullable=False)
    slot_template_id = Column(Integer, ForeignKey("slot_templates.id"), nullable=True)  # Optional reference to slot template
    time_limit_seconds = Column(Integer, nullable=True)  # Optional time cap for the slot
    required_equipment_ids = Column(JSONB, nullable=True)  # Array of equipment IDs - slot only visible if user has this equipment
    target_sets = Column(Integer, nullable=True)  # Target number of sets
    target_reps_min = Column(Integer, nullable=True)  # Target rep range minimum
    target_reps_max = Column(Integer, nullable=True)  # Target rep range maximum
    target_weight = Column(Float, nullable=True)  # Target weight
    target_time_seconds = Column(Integer, nullable=True)  # Target time (for time-based exercises)
    target_rest_seconds = Column(Integer, nullable=True)  # Target rest period
    progression_rule = Column(JSONB, nullable=True)  # Auto-progression configuration (e.g., {"type": "weight", "increment": 2.5, "trigger": "max_reps"})

    # Relationships
    routine_template = relationship("RoutineTemplate", back_populates="slots")
    workout_exercises = relationship("WorkoutExercise", back_populates="slot")
    slot_template = relationship("SlotTemplate", foreign_keys=[slot_template_id])

    def __repr__(self):
        return f"<RoutineSlot(id={self.id}, order={self.order}, routine_id={self.routine_template_id}, slot_type='{self.slot_type.value}')>"
