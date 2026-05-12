"""
챕터 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ChapterCreate(BaseModel):
    """챕터 생성 요청 스키마"""
    chapter_number: Optional[int] = Field(
        default=None,
        description="챕터 번호. 미지정 시 자동으로 마지막 번호 + 1 할당",
    )
    title: Optional[str] = None
    content: str = Field(..., min_length=1, description="챕터 본문")
    word_count: Optional[int] = Field(
        default=None,
        description="글자 수. 미지정 시 content 길이로 자동 계산",
    )


class ChapterUpdate(BaseModel):
    """챕터 수정 요청 스키마 (제공된 필드만 업데이트)"""
    title: Optional[str] = None
    content: Optional[str] = None
    word_count: Optional[int] = None
    consistency_score: Optional[int] = Field(default=None, ge=0, le=100)


class ChapterReorderRequest(BaseModel):
    """챕터 순서 변경 요청 스키마"""
    chapter_ids: List[uuid.UUID] = Field(
        ...,
        description="새 순서로 정렬된 챕터 ID 목록. 프로젝트의 모든 챕터 ID를 포함해야 합니다.",
    )


class ChapterRegenerateRequest(BaseModel):
    """챕터 재생성 요청 스키마"""
    tone_adjustment: Optional[str] = Field(
        default=None,
        description="톤 조정 지시사항 (예: '더 어둡게', '유머러스하게')",
    )
    plot_direction: Optional[str] = Field(
        default=None,
        description="플롯 방향 지시사항",
    )
    custom_instructions: Optional[str] = Field(
        default=None,
        description="사용자 정의 재생성 지시사항",
    )


class ChapterResponse(BaseModel):
    """챕터 응답 스키마"""
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


class ChapterListResponse(BaseModel):
    """챕터 목록 응답 스키마"""
    items: List[ChapterResponse]
    total: int


class ChapterVersionResponse(BaseModel):
    """챕터 버전 응답 스키마"""
    id: uuid.UUID
    chapter_id: uuid.UUID
    version_number: int
    content: str
    word_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ChapterVersionListResponse(BaseModel):
    """챕터 버전 목록 응답 스키마"""
    items: List[ChapterVersionResponse]
    total: int


class ChapterRollbackRequest(BaseModel):
    """챕터 버전 롤백 요청 스키마"""
    version_number: int = Field(..., ge=1, description="롤백할 버전 번호")
