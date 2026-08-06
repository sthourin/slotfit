"""
Exercise model with muscle group and equipment relationships
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Text,
    Float,
    Enum as SQLEnum,
    Table,
)
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class DifficultyLevel(str, enum.Enum):
    BEGINNER = "Beginner"
    NOVICE = "Novice"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"
    EXPERT = "Expert"


class SetProtocol(str, enum.Enum):
    """How an exercise's sets are measured.

    Drives which fields the gym UI prompts for. REPS and EMOM record the same
    columns today, but stay distinct because progression differs and interval
    routines need to tell them apart.
    """

    REPS = "reps"      # weight optional, reps
    TIME = "time"      # weight optional, seconds - rower, plank, carries
    AMRAP = "amrap"    # weight optional, reps, seconds - fixed window, count reps
    EMOM = "emom"      # weight optional, reps - fixed reps per interval


# A label carries two independent things: intent ("HIIT") and protocol
# ("AMRAP"/"EMOM"). Scanning tokens rather than matching whole strings lets
# compound labels like "HIIT AMRAP" work without enumerating combinations.
_PROTOCOL_TOKENS: dict[str, SetProtocol] = {
    "amrap": SetProtocol.AMRAP,
    "emom": SetProtocol.EMOM,
}


def protocol_for_variant_type(variant_type: str | None) -> SetProtocol:
    """Infer a set protocol from a variant's human label.

    "HIIT AMRAP" -> AMRAP, "EMOM" -> EMOM, "Strength" -> REPS.

    A bare "HIIT" yields REPS on purpose. It states an intent, not a
    measurement, and guessing AMRAP from it would be wrong for anyone whose
    intervals are fixed-rep.
    """
    if not variant_type:
        return SetProtocol.REPS
    for token in variant_type.lower().split():
        protocol = _PROTOCOL_TOKENS.get(token)
        if protocol is not None:
            return protocol
    return SetProtocol.REPS


# Association table for many-to-many relationship between exercises and muscle groups
exercise_muscle_groups = Table(
    "exercise_muscle_groups",
    Base.metadata,
    Column("exercise_id", Integer, ForeignKey("exercises.id"), primary_key=True),
    Column("muscle_group_id", Integer, ForeignKey("muscle_groups.id"), primary_key=True),
    Column("role", String, nullable=False),  # "target", "prime_mover", "secondary", "tertiary"
)


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Equipment relationships
    primary_equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)
    secondary_equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)
    primary_equipment_count = Column(Integer, default=1)
    secondary_equipment_count = Column(Integer, default=0)
    
    # Difficulty and classification
    difficulty = Column(SQLEnum(DifficultyLevel), nullable=True)
    exercise_classification = Column(String, nullable=True)  # e.g., "Bodybuilding", "Calisthenics"
    
    # Movement details
    posture = Column(String, nullable=True)  # e.g., "Supine", "Standing", "Prone"
    movement_pattern_1 = Column(String, nullable=True)
    movement_pattern_2 = Column(String, nullable=True)
    movement_pattern_3 = Column(String, nullable=True)
    plane_of_motion_1 = Column(String, nullable=True)
    plane_of_motion_2 = Column(String, nullable=True)
    plane_of_motion_3 = Column(String, nullable=True)
    body_region = Column(String, nullable=True)  # e.g., "Core", "Upper Body", "Lower Body"
    force_type = Column(String, nullable=True)  # e.g., "Push", "Pull", "Other"
    mechanics = Column(String, nullable=True)  # "Compound" or "Isolation"
    laterality = Column(String, nullable=True)  # e.g., "Bilateral", "Unilateral"
    
    # Media URLs
    short_demo_url = Column(String, nullable=True)
    in_depth_url = Column(String, nullable=True)
    
    # Metadata
    instructions = Column(Text, nullable=True)  # Can be populated from description or separate field
    
    # Exercise Variants (for context-aware history tracking)
    base_exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=True)  # NULL for original exercises, references id for variants
    variant_type = Column(String, nullable=True)  # "HIIT AMRAP", "HIIT EMOM", "Strength", "Volume", "Custom"
    # How sets are measured. Inferred from variant_type on creation, but stored
    # explicitly so behaviour can't be changed by editing a free-text label.
    set_protocol = Column(
        SQLEnum(SetProtocol, values_callable=lambda x: [e.value for e in x]),
        default=SetProtocol.REPS,
        server_default=SetProtocol.REPS.value,
        nullable=False,
    )
    is_custom = Column(String, default="False")  # "True" for user-created variants (using String for SQLite compatibility)
    # Default parameters for variants
    default_sets = Column(Integer, nullable=True)
    default_reps = Column(Integer, nullable=True)
    default_weight = Column(Float, nullable=True)
    default_time_seconds = Column(Integer, nullable=True)  # For time-based exercises
    default_rest_seconds = Column(Integer, nullable=True)
    # Note: user_id will be added when authentication is implemented

    # Relationships
    primary_equipment = relationship("Equipment", foreign_keys=[primary_equipment_id], back_populates="primary_exercises")
    secondary_equipment = relationship("Equipment", foreign_keys=[secondary_equipment_id], back_populates="secondary_exercises")
    muscle_groups = relationship(
        "MuscleGroup",
        secondary=exercise_muscle_groups,
        back_populates="exercises",
    )
    base_exercise = relationship("Exercise", remote_side=[id], backref="variants")  # Self-referential for variants

    def __repr__(self):
        return f"<Exercise(id={self.id}, name='{self.name}')>"


# Note: ExerciseMuscleGroup is represented by the exercise_muscle_groups Table
# The role column in the table stores the relationship type (target, prime_mover, secondary, tertiary)
