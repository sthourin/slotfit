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
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, device_id='{self.device_id}', display_name='{self.display_name}')>"
