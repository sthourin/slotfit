"""
Weekly Volume model - tracks training volume per muscle group per week
Used for periodization and volume management
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base import Base


class WeeklyVolume(Base):
    __tablename__ = "weekly_volume"

    id = Column(Integer, primary_key=True, index=True)
    muscle_group_id = Column(Integer, ForeignKey("muscle_groups.id"), nullable=False, index=True)
    week_start = Column(Date, nullable=False, index=True)  # Monday of the week (ISO week start)
    total_sets = Column(Integer, default=0, nullable=False)
    total_reps = Column(Integer, default=0, nullable=False)
    total_volume = Column(Float, default=0.0, nullable=False)  # weight × reps
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Unique constraint: one record per muscle group per week per user
    __table_args__ = (
        UniqueConstraint('muscle_group_id', 'week_start', 'user_id', name='uq_weekly_volume_muscle_group_week_user'),
    )

    # Relationships
    muscle_group = relationship("MuscleGroup", foreign_keys=[muscle_group_id])
    user = relationship("User", backref="weekly_volumes")

    def __repr__(self):
        return f"<WeeklyVolume(id={self.id}, muscle_group_id={self.muscle_group_id}, week_start={self.week_start}, sets={self.total_sets}, volume={self.total_volume})>"
