"""
세계관 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class WorldBuildingCreate(BaseModel):
    project_id: uuid.UUID
    category: str
    name: str
    description: str
    rules: Optional[Dict[str, Any]] = None


class WorldBuildingUpdate(BaseModel):
    category: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None


class WorldBuildingResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    category: str
    name: str
    description: str
    rules: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
