"""
스토리 컨텍스트 Pydantic 스키마
"""
from datetime import datetime
from typing import List

from pydantic import BaseModel

from backend.app.schemas.character import CharacterResponse
from backend.app.schemas.plot import PlotPointResponse
from backend.app.schemas.worldbuilding import WorldBuildingResponse


class StoryContext(BaseModel):
    project_id: str
    characters: List[CharacterResponse]
    plot_points: List[PlotPointResponse]
    world_building: List[WorldBuildingResponse]
    recent_chapters_summary: str = ""
    total_tokens: int = 0
    last_updated: datetime
