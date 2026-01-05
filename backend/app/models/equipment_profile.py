"""
Equipment Profile model - location-based equipment presets
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.base import Base


class EquipmentProfile(Base):
    __tablename__ = "equipment_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    equipment_ids = Column(JSONB, nullable=False)  # Array of equipment IDs
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    
    # Note: user_id deferred to future phase (MVP is offline-only)
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<EquipmentProfile(id={self.id}, name='{self.name}', is_default={self.is_default})>"
