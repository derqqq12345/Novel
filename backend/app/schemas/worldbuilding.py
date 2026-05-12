"""
세계관 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class WorldBuildingListResponse(BaseModel):
    """세계관 요소 목록 응답 스키마 (카테고리별 그룹화 포함)"""
    items: List[WorldBuildingResponse]
    total: int
    by_category: Dict[str, List[WorldBuildingResponse]]


class WorldBuildingBulkUpsertItem(BaseModel):
    """Bulk upsert 시 개별 항목 스키마 (id가 있으면 update, 없으면 create)"""
    id: Optional[uuid.UUID] = None
    category: str = Field(..., max_length=100)
    name: str = Field(..., max_length=200)
    description: str
    rules: Optional[Dict[str, Any]] = None


class WorldBuildingBulkUpdate(BaseModel):
    """세계관 요소 일괄 생성/수정 요청 스키마"""
    world_buildings: List[WorldBuildingBulkUpsertItem]
