"""
플롯 포인트 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.app.schemas.generation import PlotStage


class PlotPointCreate(BaseModel):
    project_id: uuid.UUID
    title: str
    description: Optional[str] = None
    plot_stage: PlotStage
    sequence_order: int
    target_chapter: Optional[int] = None


class PlotPointUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    plot_stage: Optional[PlotStage] = None
    sequence_order: Optional[int] = None
    is_completed: Optional[bool] = None
    target_chapter: Optional[int] = None


class PlotPointResponse(BaseModel):
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
