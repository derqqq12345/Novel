"""
소설 내보내기 스키마
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    """내보내기 형식"""
    PDF = "pdf"
    EPUB = "epub"
    TXT = "txt"


class PDFFormatOptions(BaseModel):
    """PDF 포맷 옵션"""
    font_name: str = Field(default="NotoSansKR", description="폰트 이름")
    font_size: int = Field(default=12, ge=8, le=24, description="폰트 크기 (8-24)")
    margin_top: float = Field(default=2.5, ge=1.0, le=5.0, description="상단 여백 (cm)")
    margin_bottom: float = Field(default=2.5, ge=1.0, le=5.0, description="하단 여백 (cm)")
    margin_left: float = Field(default=2.5, ge=1.0, le=5.0, description="좌측 여백 (cm)")
    margin_right: float = Field(default=2.5, ge=1.0, le=5.0, description="우측 여백 (cm)")
    line_spacing: float = Field(default=1.5, ge=1.0, le=3.0, description="줄간격 (1.0-3.0)")
    include_toc: bool = Field(default=True, description="목차 포함 여부")
    include_page_numbers: bool = Field(default=True, description="페이지 번호 포함 여부")


class ExportRequest(BaseModel):
    """내보내기 요청"""
    format: ExportFormat = Field(..., description="내보내기 형식 (pdf/epub/txt)")
    pdf_options: Optional[PDFFormatOptions] = Field(
        default=None,
        description="PDF 포맷 옵션 (format이 pdf일 때만 사용)"
    )


class ExportResponse(BaseModel):
    """내보내기 응답"""
    task_id: str = Field(..., description="비동기 작업 ID")
    status: str = Field(..., description="작업 상태 (pending/processing/completed/failed)")
    message: str = Field(..., description="상태 메시지")


class ExportStatusResponse(BaseModel):
    """내보내기 상태 조회 응답"""
    task_id: str = Field(..., description="비동기 작업 ID")
    status: str = Field(..., description="작업 상태 (pending/processing/completed/failed)")
    progress: int = Field(default=0, ge=0, le=100, description="진행률 (0-100)")
    download_url: Optional[str] = Field(default=None, description="다운로드 URL (완료 시)")
    error_message: Optional[str] = Field(default=None, description="오류 메시지 (실패 시)")
    created_at: str = Field(..., description="작업 생성 시각")
    completed_at: Optional[str] = Field(default=None, description="작업 완료 시각")
