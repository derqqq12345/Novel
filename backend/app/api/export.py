"""
소설 내보내기 API 엔드포인트
- POST /api/projects/{id}/export        소설 내보내기 (비동기)
- GET  /api/export/status/{task_id}     내보내기 상태 조회
- GET  /api/export/download/{task_id}   내보내기 파일 다운로드
"""
import logging
import uuid
from datetime import datetime
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.project import Project
from backend.app.schemas.export import (
    ExportFormat,
    ExportRequest,
    ExportResponse,
    ExportStatusResponse,
)
from backend.app.tasks.export_tasks import export_novel_task
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(tags=["소설 내보내기"])


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────


async def _get_project_or_404(
    db: AsyncSession, project_id: uuid.UUID
) -> Project:
    """프로젝트를 조회하고 없으면 404를 반환합니다."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project: Project | None = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )
    return project


def _verify_owner(project: Project, current_user_id: uuid.UUID) -> None:
    """프로젝트 소유자를 검증합니다. 소유자가 아니면 403을 반환합니다."""
    if project.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 프로젝트에 접근할 권한이 없습니다.",
        )


# ─── 소설 내보내기 ────────────────────────────────────────────────────────────


@router.post(
    "/projects/{project_id}/export",
    response_model=ExportResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="소설 내보내기",
)
async def export_novel(
    project_id: uuid.UUID,
    body: ExportRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """
    소설을 지정된 형식으로 내보냅니다 (비동기 처리).

    - 지원 형식: PDF, EPUB, TXT
    - PDF 형식의 경우 포맷 옵션을 지정할 수 있습니다
    - 비동기 작업으로 처리되며, task_id를 반환합니다
    - task_id로 작업 상태를 조회하고 완료 후 다운로드할 수 있습니다

    **권한:**
    - 프로젝트 소유자만 내보내기 가능

    **응답:**
    - 202 Accepted: 내보내기 작업이 시작됨
    - 404 Not Found: 프로젝트가 존재하지 않음
    - 403 Forbidden: 권한 없음
    """
    # 프로젝트 조회 및 권한 확인
    project = await _get_project_or_404(db, project_id)
    _verify_owner(project, current_user.id)

    # PDF 옵션 검증
    pdf_options_dict = None
    if body.format == ExportFormat.PDF and body.pdf_options:
        pdf_options_dict = body.pdf_options.model_dump()

    # Celery 태스크 시작
    task = export_novel_task.apply_async(
        args=[str(project_id), body.format.value, pdf_options_dict],
        task_id=None,  # 자동 생성
    )

    logger.info(
        "소설 내보내기 작업 시작: project_id=%s, format=%s, task_id=%s",
        project_id,
        body.format.value,
        task.id,
    )

    return ExportResponse(
        task_id=task.id,
        status="pending",
        message=f"{body.format.value.upper()} 형식으로 내보내기 작업이 시작되었습니다.",
    )


# ─── 내보내기 상태 조회 ───────────────────────────────────────────────────────


@router.get(
    "/export/status/{task_id}",
    response_model=ExportStatusResponse,
    summary="내보내기 상태 조회",
)
async def get_export_status(
    task_id: str,
    current_user: CurrentUser,
) -> ExportStatusResponse:
    """
    내보내기 작업의 상태를 조회합니다.

    **작업 상태:**
    - PENDING: 대기 중
    - PROGRESS: 처리 중
    - SUCCESS: 완료
    - FAILURE: 실패

    **응답:**
    - 200 OK: 상태 정보 반환
    - 404 Not Found: 작업을 찾을 수 없음
    """
    task_result = AsyncResult(task_id)

    # 작업 상태 확인
    if task_result.state == "PENDING":
        return ExportStatusResponse(
            task_id=task_id,
            status="pending",
            progress=0,
            created_at=datetime.now().isoformat(),
        )

    elif task_result.state == "PROGRESS":
        # 진행률 정보 가져오기
        meta = task_result.info or {}
        progress = meta.get("progress", 0)
        status_msg = meta.get("status", "처리 중...")

        return ExportStatusResponse(
            task_id=task_id,
            status="processing",
            progress=progress,
            created_at=datetime.now().isoformat(),
        )

    elif task_result.state == "SUCCESS":
        # 완료된 작업 정보
        result = task_result.result
        download_url = f"/api/export/download/{task_id}"

        return ExportStatusResponse(
            task_id=task_id,
            status="completed",
            progress=100,
            download_url=download_url,
            created_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
        )

    elif task_result.state == "FAILURE":
        # 실패한 작업
        error_message = str(task_result.info) if task_result.info else "알 수 없는 오류"

        return ExportStatusResponse(
            task_id=task_id,
            status="failed",
            progress=0,
            error_message=error_message,
            created_at=datetime.now().isoformat(),
        )

    else:
        # 알 수 없는 상태
        return ExportStatusResponse(
            task_id=task_id,
            status="unknown",
            progress=0,
            created_at=datetime.now().isoformat(),
        )


# ─── 내보내기 파일 다운로드 ───────────────────────────────────────────────────


@router.get(
    "/export/download/{task_id}",
    summary="내보내기 파일 다운로드",
)
async def download_export_file(
    task_id: str,
    current_user: CurrentUser,
) -> FileResponse:
    """
    완료된 내보내기 파일을 다운로드합니다.

    **응답:**
    - 200 OK: 파일 다운로드
    - 404 Not Found: 작업을 찾을 수 없거나 파일이 없음
    - 400 Bad Request: 작업이 아직 완료되지 않음
    """
    task_result = AsyncResult(task_id)

    # 작업 완료 확인
    if task_result.state != "SUCCESS":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"작업이 아직 완료되지 않았습니다. 현재 상태: {task_result.state}",
        )

    # 결과에서 파일 경로 가져오기
    result = task_result.result
    if not result or "file_path" not in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일 정보를 찾을 수 없습니다.",
        )

    file_path = result["file_path"]
    file_name = result["file_name"]
    export_format = result["format"]

    # 파일 존재 확인
    import os

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="파일을 찾을 수 없습니다.",
        )

    # MIME 타입 설정
    media_type_map = {
        "pdf": "application/pdf",
        "epub": "application/epub+zip",
        "txt": "text/plain; charset=utf-8",
    }
    media_type = media_type_map.get(export_format, "application/octet-stream")

    logger.info(
        "소설 내보내기 파일 다운로드: task_id=%s, file=%s",
        task_id,
        file_name,
    )

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type=media_type,
    )
