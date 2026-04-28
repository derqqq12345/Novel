"""
생성 파라미터 및 관련 스키마
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Genre(str, Enum):
    FANTASY = "fantasy"
    ROMANCE = "romance"
    MYSTERY = "mystery"
    SCIENCE_FICTION = "science_fiction"
    THRILLER = "thriller"


class Tone(str, Enum):
    SERIOUS = "serious"
    HUMOROUS = "humorous"
    DARK = "dark"
    LIGHTHEARTED = "lighthearted"


class PlotStage(str, Enum):
    EXPOSITION = "exposition"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"


class GenerationParameters(BaseModel):
    genre: Genre
    tone: Tone
    temperature: float = Field(ge=0.3, le=1.2, default=0.7)
    top_p: float = Field(ge=0.0, le=1.0, default=0.9)
    max_tokens: int = Field(ge=1000, le=8000, default=3000)
    user_prompt: Optional[str] = None


class UserFeedback(BaseModel):
    tone_adjustment: Optional[str] = None
    plot_direction: Optional[str] = None
    custom_instructions: Optional[str] = None


class GenerationLogResponse(BaseModel):
    id: uuid.UUID
    chapter_id: Optional[uuid.UUID]
    user_id: uuid.UUID
    response_time_ms: Optional[int]
    token_count: Optional[int]
    consistency_score: Optional[int]
    parameters: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
