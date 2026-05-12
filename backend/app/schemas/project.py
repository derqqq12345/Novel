"""
프로젝트 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    genre: Optional[str] = None
    description: Optional[str] = None
    ai_model: str = "qwen"


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    ai_model: Optional[str] = None
    ai_model_config: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    genre: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    total_word_count: int
    status: str
    ai_model: str
    ai_model_config: Dict[str, Any]
    chapter_count: int = 0

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int
