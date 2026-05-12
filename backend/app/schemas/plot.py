"""
플롯 포인트 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.generation import PlotStage


class PlotPointCreate(BaseModel):
    """단일 플롯 포인트 생성 스키마 (bulk upsert 내부 항목용)"""
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    plot_stage: Optional[PlotStage] = None
    sequence_order: int
    target_chapter: Optional[int] = None


class PlotPointUpdate(BaseModel):
    """단일 플롯 포인트 부분 수정 스키마"""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    plot_stage: Optional[PlotStage] = None
    sequence_order: Optional[int] = None
    is_completed: Optional[bool] = None
    target_chapter: Optional[int] = None


class PlotPointResponse(BaseModel):
    """플롯 포인트 응답 스키마"""
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: Optional[str]
    plot_stage: Optional[str]
    sequence_order: int
    is_completed: bool
    target_chapter: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class PlotPointListResponse(BaseModel):
    """플롯 포인트 목록 응답 스키마"""
    items: List[PlotPointResponse]
    total: int


class PlotBulkUpsertItem(BaseModel):
    """Bulk upsert 시 개별 항목 스키마 (id가 있으면 update, 없으면 create)"""
    id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    plot_stage: Optional[PlotStage] = None
    sequence_order: int
    target_chapter: Optional[int] = None


class PlotBulkUpdate(BaseModel):
    """플롯 포인트 일괄 생성/수정 요청 스키마"""
    plot_points: List[PlotBulkUpsertItem]


class CurrentPlotPositionResponse(BaseModel):
    """현재 플롯 위치 응답 스키마 (첫 번째 미완료 플롯 포인트)"""
    current_plot_point: Optional[PlotPointResponse]
    total_plot_points: int
    completed_count: int
