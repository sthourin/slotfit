"""Bodyweight readings - a time series, not a profile field.

Bodyweight drifts. Storing one number and applying it to all history would
silently rewrite the volume and e1RM of every past set each time it changed, so
each reading is dated and sets resolve against the reading in effect on the day
they were performed.

`source` exists because Health Connect will eventually write here alongside
manual entry, and a sync must be able to run twice without duplicating rows.
"""
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class BodyweightReading(Base):
    __tablename__ = "bodyweight_readings"
    __table_args__ = (
        # One reading per source per instant, so re-running a sync updates in
        # place while manual entry stays independent of it.
        UniqueConstraint(
            "user_id", "recorded_at", "source", name="uq_bodyweight_user_instant_source"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # In the user's preferred units (users.preferred_units), same as logged sets.
    weight = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False, index=True)
    # "manual" today; "health_connect" once that sync exists.
    source = Column(String, nullable=False, default="manual", server_default="manual")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", backref="bodyweight_readings")

    def __repr__(self):
        return (
            f"<BodyweightReading(id={self.id}, weight={self.weight}, "
            f"recorded_at={self.recorded_at})>"
        )
