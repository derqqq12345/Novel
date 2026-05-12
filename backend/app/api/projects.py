"""
프로젝트 관리 API 엔드포인트
- POST   /api/projects           프로젝트 생성
- GET    /api/projects           목록 조회 (페이지네이션)
- GET    /api/projects/{id}      상세 조회
- PUT    /api/projects/{id}      수정
- DELETE /api/projects/{id}      삭제 (cascade)
"""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.chapter import Chapter
from backend.app.models.project import Project
from backend.app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["프로젝트 관리"])


# ─── 헬퍼 ────────────────────────────────────────────────────────────────────


async def _get_chapter_count(db: AsyncSession, project_id: uuid.UUID) -> int:
    """삭제되지 않은 챕터 수를 반환합니다."""
    result = await db.execute(
        select(func.count(Chapter.id)).where(
            Chapter.project_id == project_id,
            Chapter.is_deleted.is_(False),
        )
    )
    return result.scalar_one()


async def _build_project_response(
    db: AsyncSession, project: Project
) -> ProjectResponse:
    """Project ORM 객체를 ProjectResponse로 변환합니다 (chapter_count 포함)."""
    chapter_count = await _get_chapter_count(db, project.id)
    response = ProjectResponse.model_validate(project)
    response.chapter_count = chapter_count
    return response


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


# ─── 프로젝트 생성 ────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="프로젝트 생성",
)
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    새 소설 프로젝트를 생성합니다.

    - 인증된 사용자만 접근 가능
    - 생성된 프로젝트의 소유자는 요청한 사용자로 설정됩니다
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    project = Project(
        id=uuid.uuid4(),
        user_id=current_user.id,
        title=body.title,
        genre=body.genre,
        description=body.description,
        ai_model=body.ai_model,
        ai_model_config={},
        total_word_count=0,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    await db.flush()

    return await _build_project_response(db, project)


# ─── 프로젝트 목록 조회 ───────────────────────────────────────────────────────


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="프로젝트 목록 조회",
)
async def list_projects(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="페이지 크기 (최대 100)")] = 20,
) -> ProjectListResponse:
    """
    현재 사용자의 프로젝트 목록을 페이지네이션으로 반환합니다.

    - `updated_at` 내림차순 정렬
    - 최대 페이지 크기: 100
    """
    base_where = Project.user_id == current_user.id

    # 전체 개수 조회
    count_result = await db.execute(
        select(func.count(Project.id)).where(base_where)
    )
    total: int = count_result.scalar_one()

    # 페이지네이션 적용 목록 조회
    offset = (page - 1) * page_size
    projects_result = await db.execute(
        select(Project)
        .where(base_where)
        .order_by(Project.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    projects = list(projects_result.scalars().all())

    # 각 프로젝트의 chapter_count 조회
    items: list[ProjectResponse] = []
    for project in projects:
        items.append(await _build_project_response(db, project))

    return ProjectListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ─── 프로젝트 상세 조회 ───────────────────────────────────────────────────────


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="프로젝트 상세 조회",
)
async def get_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    특정 프로젝트의 상세 정보를 반환합니다.

    - 404: 프로젝트가 존재하지 않는 경우
    - 403: 요청한 사용자가 프로젝트 소유자가 아닌 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_owner(project, current_user.id)
    return await _build_project_response(db, project)


# ─── 프로젝트 수정 ────────────────────────────────────────────────────────────


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="프로젝트 수정",
)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    프로젝트 정보를 부분 업데이트합니다.

    - 제공된 필드만 업데이트됩니다 (partial update)
    - 404: 프로젝트가 존재하지 않는 경우
    - 403: 요청한 사용자가 프로젝트 소유자가 아닌 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_owner(project, current_user.id)

    # 제공된 필드만 업데이트
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    # updated_at 명시적 갱신 (onupdate는 flush 시 적용되지 않을 수 있음)
    project.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.flush()

    return await _build_project_response(db, project)


# ─── 프로젝트 삭제 ────────────────────────────────────────────────────────────


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="프로젝트 삭제",
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    프로젝트를 삭제합니다.

    - DB 외래 키 ON DELETE CASCADE에 의해 연관 데이터(챕터, 캐릭터 등)도 함께 삭제됩니다
    - 404: 프로젝트가 존재하지 않는 경우
    - 403: 요청한 사용자가 프로젝트 소유자가 아닌 경우
    - 성공 시 204 No Content 반환
    """
    project = await _get_project_or_404(db, project_id)
    _verify_owner(project, current_user.id)

    await db.delete(project)
    await db.flush()
