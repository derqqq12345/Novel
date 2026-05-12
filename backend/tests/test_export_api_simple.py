"""
소설 내보내기 API 간단한 테스트
"""
import pytest


def test_export_schemas_import():
    """스키마 임포트 테스트"""
    from backend.app.schemas.export import (
        ExportFormat,
        ExportRequest,
        ExportResponse,
        ExportStatusResponse,
        PDFFormatOptions,
    )

    # 스키마 생성 테스트
    pdf_options = PDFFormatOptions(
        font_size=12,
        line_spacing=1.5,
        include_toc=True,
    )
    assert pdf_options.font_size == 12
    assert pdf_options.line_spacing == 1.5

    export_request = ExportRequest(
        format=ExportFormat.PDF,
        pdf_options=pdf_options,
    )
    assert export_request.format == ExportFormat.PDF
    assert export_request.pdf_options is not None


def test_export_service_import():
    """서비스 임포트 테스트"""
    from backend.app.services.export_service import ExportService, export_service

    assert export_service is not None
    assert isinstance(export_service, ExportService)


def test_export_tasks_import():
    """태스크 임포트 테스트"""
    from backend.app.tasks.export_tasks import export_novel_task

    assert export_novel_task is not None
    assert export_novel_task.name == "export_tasks.export_novel_task"


def test_export_api_import():
    """API 라우터 임포트 테스트"""
    from backend.app.api.export import router

    assert router is not None
    assert len(router.routes) > 0

    # 라우트 확인
    route_paths = [route.path for route in router.routes]
    assert "/projects/{project_id}/export" in route_paths
    assert "/export/status/{task_id}" in route_paths
    assert "/export/download/{task_id}" in route_paths


def test_pdf_format_options_validation():
    """PDF 포맷 옵션 검증 테스트"""
    from pydantic import ValidationError

    from backend.app.schemas.export import PDFFormatOptions

    # 정상 값
    options = PDFFormatOptions(font_size=12)
    assert options.font_size == 12

    # 범위 초과 값
    with pytest.raises(ValidationError):
        PDFFormatOptions(font_size=30)  # 최대 24

    with pytest.raises(ValidationError):
        PDFFormatOptions(font_size=5)  # 최소 8


def test_export_format_enum():
    """내보내기 형식 Enum 테스트"""
    from backend.app.schemas.export import ExportFormat

    assert ExportFormat.PDF.value == "pdf"
    assert ExportFormat.EPUB.value == "epub"
    assert ExportFormat.TXT.value == "txt"

    # 모든 형식 확인
    formats = [f.value for f in ExportFormat]
    assert "pdf" in formats
    assert "epub" in formats
    assert "txt" in formats
