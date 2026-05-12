"""
세계관 설정 관리 API 엔드포인트

- GET  /api/projects/{project_id}/worldbuilding  세계관 요소 목록 조회 (카테고리별 그룹화)
- PUT  /api/projects/{project_id}/worldbuilding  세계관 요소 일괄 생성/수정 (bulk upsert)

지원 카테고리: location, magic_system, technology, culture (및 기타 사용자 정의 카테고리)
"""
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.project import Project
from backend.app.models.worldbuilding import WorldBuilding
from backend.app.schemas.worldbuilding import (
    WorldBuildingBulkUpdate,
    WorldBuildingListResponse,
    WorldBuildingResponse,
)

router = APIRouter(tags=["세계관 설정 관리"])


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


async def _get_worldbuilding_or_404(
    db: AsyncSession,
    worldbuilding_id: uuid.UUID,
) -> WorldBuilding:
    """세계관 요소를 조회하고 없으면 404를 반환합니다."""
    result = await db.execute(
        select(WorldBuilding).where(WorldBuilding.id == worldbuilding_id)
    )
    wb: WorldBuilding | None = result.scalar_one_or_none()
    if wb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세계관 요소를 찾을 수 없습니다.",
        )
    return wb


def _build_list_response(world_buildings: list[WorldBuilding]) -> WorldBuildingListResponse:
    """WorldBuilding ORM 목록을 WorldBuildingListResponse로 변환합니다 (카테고리별 그룹화 포함)."""
    items = [WorldBuildingResponse.model_validate(wb) for wb in world_buildings]

    by_category: dict[str, list[WorldBuildingResponse]] = defaultdict(list)
    for item in items:
        by_category[item.category].append(item)

    return WorldBuildingListResponse(
        items=items,
        total=len(items),
        by_category=dict(by_category),
    )


# ─── 세계관 요소 목록 조회 ────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/worldbuilding",
    response_model=WorldBuildingListResponse,
    summary="세계관 요소 목록 조회",
)
async def list_worldbuilding(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WorldBuildingListResponse:
    """
    프로젝트의 모든 세계관 요소를 카테고리별로 그룹화하여 반환합니다.

    지원 카테고리: `location`, `magic_system`, `technology`, `culture` (및 기타 사용자 정의 카테고리)

    응답의 `by_category` 필드에서 카테고리별로 그룹화된 요소를 확인할 수 있습니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    result = await db.execute(
        select(WorldBuilding)
        .where(WorldBuilding.project_id == project_id)
        .order_by(WorldBuilding.category.asc(), WorldBuilding.created_at.asc())
    )
    world_buildings = list(result.scalars().all())

    return _build_list_response(world_buildings)


# ─── 세계관 요소 일괄 생성/수정 ───────────────────────────────────────────────


@router.put(
    "/projects/{project_id}/worldbuilding",
    response_model=WorldBuildingListResponse,
    summary="세계관 요소 일괄 생성/수정 (Bulk Upsert)",
)
async def bulk_upsert_worldbuilding(
    project_id: uuid.UUID,
    body: WorldBuildingBulkUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WorldBuildingListResponse:
    """
    프로젝트의 세계관 요소를 일괄 생성하거나 수정합니다.

    - `id`가 있는 항목: 기존 세계관 요소를 수정합니다.
    - `id`가 없는 항목: 새 세계관 요소를 생성합니다.
    - 요청에 포함되지 않은 기존 세계관 요소는 삭제되지 않습니다.

    지원 카테고리: `location`, `magic_system`, `technology`, `culture` (및 기타 사용자 정의 카테고리)

    - 403: 프로젝트 소유자가 아닌 경우, 또는 수정 대상 요소가 이 프로젝트에 속하지 않는 경우
    - 404: 프로젝트 또는 수정 대상 세계관 요소가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for item in body.world_buildings:
        if item.id is not None:
            # 기존 세계관 요소 수정
            wb = await _get_worldbuilding_or_404(db, item.id)
            # 해당 요소가 이 프로젝트에 속하는지 확인
            if wb.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="이 세계관 요소는 해당 프로젝트에 속하지 않습니다.",
                )
            wb.category = item.category
            wb.name = item.name
            wb.description = item.description
            wb.rules = item.rules
            wb.updated_at = now
        else:
            # 새 세계관 요소 생성
            wb = WorldBuilding(
                id=uuid.uuid4(),
                project_id=project_id,
                category=item.category,
                name=item.name,
                description=item.description,
                rules=item.rules,
                created_at=now,
                updated_at=now,
            )
            db.add(wb)

    await db.flush()

    # 전체 목록 재조회 (카테고리 오름차순, 생성일 오름차순)
    result = await db.execute(
        select(WorldBuilding)
        .where(WorldBuilding.project_id == project_id)
        .order_by(WorldBuilding.category.asc(), WorldBuilding.created_at.asc())
    )
    all_world_buildings = list(result.scalars().all())

    return _build_list_response(all_world_buildings)
