"""
챕터 관리 API 엔드포인트

- POST   /api/projects/{project_id}/chapters/generate   챕터 생성
- GET    /api/projects/{project_id}/chapters            챕터 목록 조회
- POST   /api/projects/{project_id}/chapters/reorder    챕터 순서 변경
- GET    /api/chapters/{chapter_id}                     챕터 상세 조회
- PUT    /api/chapters/{chapter_id}                     챕터 수정
- DELETE /api/chapters/{chapter_id}                     챕터 삭제
- POST   /api/chapters/{chapter_id}/regenerate          챕터 재생성
- GET    /api/chapters/{chapter_id}/versions            챕터 버전 히스토리
- POST   /api/chapters/{chapter_id}/versions/rollback   특정 버전으로 롤백
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.project import Project
from backend.app.schemas.chapter import (
    ChapterCreate,
    ChapterListResponse,
    ChapterRegenerateRequest,
    ChapterReorderRequest,
    ChapterResponse,
    ChapterRollbackRequest,
    ChapterUpdate,
    ChapterVersionListResponse,
    ChapterVersionResponse,
)
from backend.app.services.chapter_manager import (
    ChapterManagerService,
    ChapterNotFoundError,
    ChapterNumberConflictError,
    ChapterVersionNotFoundError,
    chapter_manager,
)
from sqlalchemy import select

router = APIRouter(tags=["챕터 관리"])


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────


async def _get_project_or_404(
    db: AsyncSession,
    project_id: uuid.UUID,
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


def _verify_project_owner(project: Project, current_user_id: uuid.UUID) -> None:
    """프로젝트 소유자를 검증합니다. 소유자가 아니면 403을 반환합니다."""
    if project.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 프로젝트에 접근할 권한이 없습니다.",
        )


async def _get_chapter_and_verify_owner(
    db: AsyncSession,
    chapter_id: uuid.UUID,
    current_user_id: uuid.UUID,
    service: ChapterManagerService = chapter_manager,
) -> "Chapter":  # type: ignore[name-defined]
    """챕터를 조회하고 소유자를 검증합니다."""
    try:
        chapter = await service.get_chapter(db, chapter_id)
    except ChapterNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챕터를 찾을 수 없습니다.",
        )

    # 프로젝트 소유자 확인
    project = await _get_project_or_404(db, chapter.project_id)
    _verify_project_owner(project, current_user_id)

    return chapter


# ─── 프로젝트 하위 챕터 엔드포인트 ───────────────────────────────────────────


@router.post(
    "/projects/{project_id}/chapters/generate",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="챕터 생성",
)
async def create_chapter(
    project_id: uuid.UUID,
    body: ChapterCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterResponse:
    """
    프로젝트에 새 챕터를 생성합니다.

    - `chapter_number`를 지정하지 않으면 현재 마지막 챕터 번호 + 1로 자동 설정됩니다.
    - `word_count`를 지정하지 않으면 `content` 길이로 자동 계산됩니다.
    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    - 409: 지정한 챕터 번호가 이미 존재하는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    try:
        chapter = await chapter_manager.create_chapter(db, project_id, body)
    except ChapterNumberConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return ChapterResponse.model_validate(chapter)


@router.get(
    "/projects/{project_id}/chapters",
    response_model=ChapterListResponse,
    summary="챕터 목록 조회",
)
async def list_chapters(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterListResponse:
    """
    프로젝트의 모든 챕터를 챕터 번호 오름차순으로 반환합니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    chapters = await chapter_manager.get_chapters_by_project(db, project_id)
    items = [ChapterResponse.model_validate(ch) for ch in chapters]
    return ChapterListResponse(items=items, total=len(items))


@router.post(
    "/projects/{project_id}/chapters/reorder",
    response_model=ChapterListResponse,
    summary="챕터 순서 변경",
)
async def reorder_chapters(
    project_id: uuid.UUID,
    body: ChapterReorderRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterListResponse:
    """
    챕터 순서를 재정렬합니다.

    `chapter_ids` 리스트의 순서대로 챕터 번호가 1부터 연속적으로 재할당됩니다.
    리스트에는 프로젝트의 **모든** 활성 챕터 ID가 포함되어야 합니다.

    - 400: chapter_ids가 프로젝트의 챕터 목록과 일치하지 않는 경우
    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    try:
        chapters = await chapter_manager.reorder_chapters(db, project_id, body.chapter_ids)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    items = [ChapterResponse.model_validate(ch) for ch in chapters]
    return ChapterListResponse(items=items, total=len(items))


# ─── 챕터 단일 엔드포인트 ─────────────────────────────────────────────────────


@router.get(
    "/chapters/{chapter_id}",
    response_model=ChapterResponse,
    summary="챕터 상세 조회",
)
async def get_chapter(
    chapter_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterResponse:
    """
    챕터 상세 정보를 반환합니다.

    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    chapter = await _get_chapter_and_verify_owner(db, chapter_id, current_user.id)
    return ChapterResponse.model_validate(chapter)


@router.put(
    "/chapters/{chapter_id}",
    response_model=ChapterResponse,
    summary="챕터 수정",
)
async def update_chapter(
    chapter_id: uuid.UUID,
    body: ChapterUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterResponse:
    """
    챕터를 수정합니다.

    - 제공된 필드만 업데이트됩니다 (partial update).
    - `content`가 변경되면 현재 내용이 자동으로 버전으로 저장됩니다 (최대 5개 유지).
    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    await _get_chapter_and_verify_owner(db, chapter_id, current_user.id)

    try:
        chapter = await chapter_manager.update_chapter(db, chapter_id, body)
    except ChapterNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챕터를 찾을 수 없습니다.",
        )

    return ChapterResponse.model_validate(chapter)


@router.delete(
    "/chapters/{chapter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="챕터 삭제",
)
async def delete_chapter(
    chapter_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    챕터를 삭제합니다 (소프트 삭제).

    - 성공 시 204 No Content 반환
    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    await _get_chapter_and_verify_owner(db, chapter_id, current_user.id)

    try:
        await chapter_manager.delete_chapter(db, chapter_id)
    except ChapterNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챕터를 찾을 수 없습니다.",
        )


@router.post(
    "/chapters/{chapter_id}/regenerate",
    response_model=ChapterResponse,
    summary="챕터 재생성",
)
async def regenerate_chapter(
    chapter_id: uuid.UUID,
    body: ChapterRegenerateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterResponse:
    """
    챕터를 재생성합니다.

    현재 챕터 내용을 버전으로 보존한 뒤, 사용자 피드백(톤 조정, 플롯 방향 등)을
    반영하여 새 내용을 생성합니다.

    > **참고**: 현재 구현은 AI 생성 서비스(Phase 5)가 완성되기 전까지
    > 피드백을 챕터 메타데이터에 기록하는 플레이스홀더로 동작합니다.
    > Phase 5 완료 후 실제 AI 재생성 로직으로 교체됩니다.

    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    chapter = await _get_chapter_and_verify_owner(db, chapter_id, current_user.id)

    # TODO: Phase 5 (AI 통합) 완료 후 실제 재생성 로직으로 교체
    # 현재는 피드백 정보를 챕터 제목에 임시 기록하는 플레이스홀더
    feedback_parts = []
    if body.tone_adjustment:
        feedback_parts.append(f"톤: {body.tone_adjustment}")
    if body.plot_direction:
        feedback_parts.append(f"플롯: {body.plot_direction}")
    if body.custom_instructions:
        feedback_parts.append(body.custom_instructions)

    # 피드백이 있으면 현재 버전을 저장하고 제목에 피드백 메모 추가
    if feedback_parts:
        update_data = ChapterUpdate(
            title=f"[재생성 대기] {chapter.title or ''} ({', '.join(feedback_parts)})".strip()
        )
        try:
            chapter = await chapter_manager.update_chapter(db, chapter_id, update_data)
        except ChapterNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="챕터를 찾을 수 없습니다.",
            )

    return ChapterResponse.model_validate(chapter)


@router.get(
    "/chapters/{chapter_id}/versions",
    response_model=ChapterVersionListResponse,
    summary="챕터 버전 히스토리 조회",
)
async def get_chapter_versions(
    chapter_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterVersionListResponse:
    """
    챕터의 버전 히스토리를 최신순으로 반환합니다 (최대 5개).

    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    await _get_chapter_and_verify_owner(db, chapter_id, current_user.id)

    try:
        versions = await chapter_manager.get_chapter_versions(db, chapter_id)
    except ChapterNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챕터를 찾을 수 없습니다.",
        )

    items = [ChapterVersionResponse.model_validate(v) for v in versions]
    return ChapterVersionListResponse(items=items, total=len(items))


@router.post(
    "/chapters/{chapter_id}/versions/rollback",
    response_model=ChapterResponse,
    summary="챕터 버전 롤백",
)
async def rollback_chapter_version(
    chapter_id: uuid.UUID,
    body: ChapterRollbackRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChapterResponse:
    """
    챕터를 특정 버전으로 롤백합니다.

    롤백 전 현재 내용이 새 버전으로 자동 저장됩니다.

    - 400: 지정한 버전이 존재하지 않는 경우
    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    await _get_chapter_and_verify_owner(db, chapter_id, current_user.id)

    try:
        chapter = await chapter_manager.rollback_to_version(
            db, chapter_id, body.version_number
        )
    except ChapterNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챕터를 찾을 수 없습니다.",
        )
    except ChapterVersionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ChapterResponse.model_validate(chapter)
