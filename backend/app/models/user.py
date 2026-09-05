"""
User model - supports both device-based (MVP) and authenticated users (future)
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.sql import func

from app.models.base import Base


class User(Base):
    """User model - supports both device-based (MVP) and authenticated users (future)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    
    # Device-based identification (MVP)
    device_id = Column(String, unique=True, index=True, nullable=True)
    
    # Future auth fields (nullable for now)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    
    # Profile info
    display_name = Column(String, default="Athlete")
    
    # Preferences (can expand later)
    preferred_units = Column(String, default="lbs")  # "lbs" or "kg"

    # Maximum heart rate, the basis for every zone boundary. A single column
    # rather than a dated log like `bodyweight_readings`, because the two change
    # for opposite reasons: a past weigh-in was true when taken, while a past
    # max HR was only ever an estimate, so a better figure should recompute
    # history rather than apply from its own date forward. Zones are derived
    # from `bpm`, never stored, which makes that recompute cheap.
    #
    # Nullable on purpose: with no value, no zones are computed at all. A
    # guessed maximum would define every boundary while looking authoritative.
    max_hr = Column(Integer, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, device_id='{self.device_id}', display_name='{self.display_name}')>"
