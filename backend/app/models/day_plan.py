"""
Day Plan models - pattern-coverage goals replacing routine templates
"""
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class DayPlan(Base):
    __tablename__ = "day_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    warmup_preferences = Column(JSONB, nullable=False, default=list)  # ordered exercise ids, most preferred first
    rounds_target = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", backref="day_plans")
    goals = relationship(
        "PatternGoal",
        back_populates="day_plan",
        cascade="all, delete-orphan",
        order_by="PatternGoal.id",
    )

    def __repr__(self):
        return f"<DayPlan(id={self.id}, name='{self.name}')>"


class PatternGoal(Base):
    __tablename__ = "pattern_goals"

    id = Column(Integer, primary_key=True, index=True)
    day_plan_id = Column(Integer, ForeignKey("day_plans.id"), nullable=False, index=True)
    pattern_id = Column(Integer, ForeignKey("movement_patterns.id"), nullable=False)
    required = Column(Boolean, default=True, nullable=False)
    target_sets = Column(Integer, nullable=True)
    rep_range_min = Column(Integer, nullable=True)  # service default 8 when unset
    rep_range_max = Column(Integer, nullable=True)  # service default 12 when unset

    day_plan = relationship("DayPlan", back_populates="goals")
    pattern = relationship("MovementPattern")

    def __repr__(self):
        return f"<PatternGoal(id={self.id}, day_plan_id={self.day_plan_id}, pattern_id={self.pattern_id})>"
