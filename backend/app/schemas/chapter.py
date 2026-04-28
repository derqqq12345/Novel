"""
챕터 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChapterCreate(BaseModel):
    project_id: uuid.UUID
    chapter_number: int
    title: Optional[str] = None
    content: str
    word_count: int


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    word_count: Optional[int] = None
    consistency_score: Optional[int] = None


class ChapterResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    chapter_number: int
    title: Optional[str]
    content: str
    word_count: int
    consistency_score: Optional[int]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = {"from_attributes": True}


class ChapterVersionResponse(BaseModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    version_number: int
    content: str
    word_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
