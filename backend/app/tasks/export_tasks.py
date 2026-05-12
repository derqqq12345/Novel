"""
Celery 태스크: 소설 내보내기 비동기 작업

PDF, EPUB, TXT 형식으로 소설을 내보내는 비동기 작업을 처리합니다.
"""
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from backend.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="export_tasks.export_novel_task",
    max_retries=2,
    default_retry_delay=30,
    time_limit=120,  # 2분 타임아웃
    soft_time_limit=100,  # 100초 소프트 타임아웃
)
def export_novel_task(
    self,
    project_id: str,
    export_format: str,
    pdf_options_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    소설 내보내기 Celery 태스크.

    ExportService를 사용하여 소설을 지정된 형식으로 내보냅니다.

    Args:
        project_id: 프로젝트 ID (문자열)
        export_format: 내보내기 형식 (pdf/epub/txt)
        pdf_options_dict: PDF 포맷 옵션 딕셔너리 (선택)

    Returns:
        내보내기 결과 딕셔너리:
        {
            "status": "completed",
            "file_path": str,
            "file_name": str,
            "file_size": int,
            "format": str
        }

    Raises:
        celery.exceptions.Retry: 재시도 가능한 오류 발생 시
    """
    logger.info(
        "소설 내보내기 태스크 시작: project_id=%s, format=%s",
        project_id,
        export_format,
    )

    # 진행률 업데이트
    self.update_state(state="PROGRESS", meta={"progress": 10, "status": "초기화 중..."})

    async def _run() -> Dict[str, Any]:
        from backend.app.database import AsyncSessionLocal
        from backend.app.schemas.export import PDFFormatOptions
        from backend.app.services.export_service import export_service

        project_uuid = uuid.UUID(project_id)

        async with AsyncSessionLocal() as db:
            # 진행률 업데이트
            self.update_state(
                state="PROGRESS", meta={"progress": 30, "status": "챕터 조회 중..."}
            )

            # 형식에 따라 내보내기 실행
            output_path: Path
            if export_format == "pdf":
                pdf_options = None
                if pdf_options_dict:
                    pdf_options = PDFFormatOptions(**pdf_options_dict)

                self.update_state(
                    state="PROGRESS", meta={"progress": 50, "status": "PDF 생성 중..."}
                )
                output_path = await export_service.export_to_pdf(
                    db, project_uuid, pdf_options
                )

            elif export_format == "epub":
                self.update_state(
                    state="PROGRESS", meta={"progress": 50, "status": "EPUB 생성 중..."}
                )
                output_path = await export_service.export_to_epub(db, project_uuid)

            elif export_format == "txt":
                self.update_state(
                    state="PROGRESS", meta={"progress": 50, "status": "TXT 생성 중..."}
                )
                output_path = await export_service.export_to_txt(db, project_uuid)

            else:
                raise ValueError(f"지원하지 않는 형식입니다: {export_format}")

            # 파일 정보 수집
            file_size = output_path.stat().st_size

            self.update_state(
                state="PROGRESS", meta={"progress": 90, "status": "완료 처리 중..."}
            )

            return {
                "status": "completed",
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "format": export_format,
            }

    try:
        result = asyncio.run(_run())
        logger.info(
            "소설 내보내기 태스크 완료: project_id=%s, file=%s",
            project_id,
            result.get("file_name"),
        )
        return result

    except ValueError as exc:
        # 검증 오류는 재시도하지 않음
        logger.error(
            "소설 내보내기 태스크 검증 오류: project_id=%s, error=%s",
            project_id,
            exc,
        )
        raise

    except Exception as exc:
        logger.error(
            "소설 내보내기 태스크 실패: project_id=%s, error=%s",
            project_id,
            exc,
            exc_info=True,
        )
        # 재시도 가능한 오류인 경우 Celery 재시도
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "소설 내보내기 태스크 최대 재시도 초과: project_id=%s",
                project_id,
            )
            raise
