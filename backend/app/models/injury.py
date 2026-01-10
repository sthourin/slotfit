"""
Injury models for tracking user injuries and movement restrictions
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text, Boolean, Table, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.base import Base

# Association table for injury -> restricted movement patterns
injury_movement_restrictions = Table(
    "injury_movement_restrictions",
    Base.metadata,
    Column("injury_type_id", Integer, ForeignKey("injury_types.id"), primary_key=True),
    Column("restriction_id", Integer, ForeignKey("movement_restrictions.id"), primary_key=True),
)


class InjuryType(Base):
    """Injury types with their movement restrictions - can be system-defined or user-created"""
    __tablename__ = "injury_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "Rotator Cuff Injury"
    body_area = Column(String, nullable=False)  # e.g., "Shoulder", "Knee", "Lumbar Spine"
    description = Column(Text, nullable=True)  # Brief description
    severity_levels = Column(JSONB, default=["mild", "moderate", "severe"])
    is_system = Column(Boolean, default=False)  # True for seeded/predefined injuries, False for user-created
    user_id = Column(Integer, nullable=True)  # NULL for system injuries, set for user-created (when auth added)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    restrictions = relationship(
        "MovementRestriction",
        secondary=injury_movement_restrictions,
        back_populates="injuries"
    )
    user_injuries = relationship("UserInjury", back_populates="injury_type")


class MovementRestriction(Base):
    """Movement patterns or exercise attributes to avoid"""
    __tablename__ = "movement_restrictions"

    id = Column(Integer, primary_key=True, index=True)
    restriction_type = Column(String, nullable=False)  # "movement_pattern", "force_type", "plane_of_motion", "posture"
    restriction_value = Column(String, nullable=False)  # e.g., "Overhead Press", "Push", "Sagittal"
    severity_threshold = Column(String, default="mild")  # Applies at this severity and above
    
    # Relationships
    injuries = relationship(
        "InjuryType",
        secondary=injury_movement_restrictions,
        back_populates="restrictions"
    )


class UserInjury(Base):
    """User's active injuries"""
    __tablename__ = "user_injuries"

    id = Column(Integer, primary_key=True, index=True)
    injury_type_id = Column(Integer, ForeignKey("injury_types.id"), nullable=False)
    severity = Column(String, default="moderate")  # mild, moderate, severe
    notes = Column(Text, nullable=True)  # User's notes about their condition
    is_active = Column(Boolean, default=True)  # Can mark as healed without deleting
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    injury_type = relationship("InjuryType", back_populates="user_injuries")
    user = relationship("User", backref="user_injuries")