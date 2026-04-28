"""
내러티브 아크 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ForeshadowingElementResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    chapter_id: uuid.UUID
    text_excerpt: str
    description: str
    is_resolved: bool
    resolved_in_chapter_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterEmotionalArcResponse(BaseModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    overall_intensity: float
    tension_curve: List[float]
    dominant_emotion: Optional[str]
    narrative_cohesion_score: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}
