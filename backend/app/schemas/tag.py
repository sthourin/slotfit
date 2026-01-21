"""
Pydantic schemas for Tag API
"""
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

from app.models.tag import Tag


class TagBase(BaseModel):
    name: str
    category: Optional[str] = None


class Tag(TagBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class TagCreate(TagBase):
    pass


class TagListResponse(BaseModel):
    tags: List[Tag]
    total: int
    skip: int
    limit: int
