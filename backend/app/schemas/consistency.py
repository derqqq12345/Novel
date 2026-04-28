"""
일관성 검증 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ConsistencyIssueResponse(BaseModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    issue_type: str
    severity: str
    description: str
    line_number: Optional[int]
    detected_at: datetime
    is_resolved: bool

    model_config = {"from_attributes": True}


class ConsistencyReport(BaseModel):
    chapter_id: uuid.UUID
    score: int = Field(ge=0, le=100)
    issues: List[ConsistencyIssueResponse]
    checked_at: datetime
