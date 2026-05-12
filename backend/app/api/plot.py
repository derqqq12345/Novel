"""
플롯 구조 관리 API 엔드포인트

- GET   /api/projects/{project_id}/plot                          프로젝트 플롯 포인트 목록 조회
- PUT   /api/projects/{project_id}/plot                          플롯 포인트 일괄 생성/수정 (bulk upsert)
- PATCH /api/projects/{project_id}/plot/{plot_point_id}/complete 플롯 포인트 완료 표시
- GET   /api/projects/{project_id}/plot/current                  현재 플롯 위치 조회 (첫 번째 미완료 포인트)
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.plot import PlotPoint
from backend.app.models.project import Project
from backend.app.schemas.plot import (
    CurrentPlotPositionResponse,
    PlotBulkUpdate,
    PlotPointListResponse,
    PlotPointResponse,
)

router = APIRouter(tags=["플롯 구조 관리"])


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


async def _get_plot_point_or_404(
    db: AsyncSession,
    plot_point_id: uuid.UUID,
) -> PlotPoint:
    """플롯 포인트를 조회하고 없으면 404를 반환합니다."""
    result = await db.execute(
        select(PlotPoint).where(PlotPoint.id == plot_point_id)
    )
    plot_point: PlotPoint | None = result.scalar_one_or_none()
    if plot_point is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="플롯 포인트를 찾을 수 없습니다.",
        )
    return plot_point


# ─── 플롯 포인트 목록 조회 ────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/plot",
    response_model=PlotPointListResponse,
    summary="플롯 포인트 목록 조회",
)
async def list_plot_points(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlotPointListResponse:
    """
    프로젝트의 모든 플롯 포인트를 sequence_order 오름차순으로 반환합니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    result = await db.execute(
        select(PlotPoint)
        .where(PlotPoint.project_id == project_id)
        .order_by(PlotPoint.sequence_order.asc())
    )
    plot_points = list(result.scalars().all())

    items = [PlotPointResponse.model_validate(pp) for pp in plot_points]
    return PlotPointListResponse(items=items, total=len(items))


# ─── 플롯 포인트 일괄 생성/수정 ───────────────────────────────────────────────


@router.put(
    "/projects/{project_id}/plot",
    response_model=PlotPointListResponse,
    summary="플롯 포인트 일괄 생성/수정 (Bulk Upsert)",
)
async def bulk_upsert_plot_points(
    project_id: uuid.UUID,
    body: PlotBulkUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlotPointListResponse:
    """
    프로젝트의 플롯 포인트를 일괄 생성하거나 수정합니다.

    - `id`가 있는 항목: 기존 플롯 포인트를 수정합니다.
    - `id`가 없는 항목: 새 플롯 포인트를 생성합니다.
    - 요청에 포함되지 않은 기존 플롯 포인트는 삭제되지 않습니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트 또는 수정 대상 플롯 포인트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    upserted_ids: list[uuid.UUID] = []

    for item in body.plot_points:
        if item.id is not None:
            # 기존 플롯 포인트 수정
            plot_point = await _get_plot_point_or_404(db, item.id)
            # 해당 플롯 포인트가 이 프로젝트에 속하는지 확인
            if plot_point.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="이 플롯 포인트는 해당 프로젝트에 속하지 않습니다.",
                )
            plot_point.title = item.title
            plot_point.description = item.description
            plot_point.plot_stage = item.plot_stage.value if item.plot_stage else None
            plot_point.sequence_order = item.sequence_order
            plot_point.target_chapter = item.target_chapter
            upserted_ids.append(plot_point.id)
        else:
            # 새 플롯 포인트 생성
            plot_point = PlotPoint(
                id=uuid.uuid4(),
                project_id=project_id,
                title=item.title,
                description=item.description,
                plot_stage=item.plot_stage.value if item.plot_stage else None,
                sequence_order=item.sequence_order,
                is_completed=False,
                target_chapter=item.target_chapter,
                created_at=now,
            )
            db.add(plot_point)
            upserted_ids.append(plot_point.id)

    await db.flush()

    # 전체 목록 재조회 (sequence_order 오름차순)
    result = await db.execute(
        select(PlotPoint)
        .where(PlotPoint.project_id == project_id)
        .order_by(PlotPoint.sequence_order.asc())
    )
    all_plot_points = list(result.scalars().all())

    items = [PlotPointResponse.model_validate(pp) for pp in all_plot_points]
    return PlotPointListResponse(items=items, total=len(items))


# ─── 플롯 포인트 완료 표시 ────────────────────────────────────────────────────


@router.patch(
    "/projects/{project_id}/plot/{plot_point_id}/complete",
    response_model=PlotPointResponse,
    summary="플롯 포인트 완료 표시",
)
async def complete_plot_point(
    project_id: uuid.UUID,
    plot_point_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlotPointResponse:
    """
    특정 플롯 포인트를 완료 상태로 표시합니다.

    이미 완료된 플롯 포인트에 대해서도 멱등적으로 동작합니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트 또는 플롯 포인트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    plot_point = await _get_plot_point_or_404(db, plot_point_id)
    if plot_point.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="플롯 포인트를 찾을 수 없습니다.",
        )

    plot_point.is_completed = True
    await db.flush()

    return PlotPointResponse.model_validate(plot_point)


# ─── 현재 플롯 위치 조회 ──────────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/plot/current",
    response_model=CurrentPlotPositionResponse,
    summary="현재 플롯 위치 조회",
)
async def get_current_plot_position(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CurrentPlotPositionResponse:
    """
    현재 플롯 위치를 반환합니다.

    현재 플롯 위치는 `is_completed = False`인 플롯 포인트 중
    `sequence_order`가 가장 낮은 항목입니다.

    모든 플롯 포인트가 완료된 경우 `current_plot_point`는 `null`을 반환합니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    # 전체 개수 조회
    total_result = await db.execute(
        select(func.count(PlotPoint.id)).where(PlotPoint.project_id == project_id)
    )
    total_count: int = total_result.scalar_one()

    # 완료된 개수 조회
    completed_result = await db.execute(
        select(func.count(PlotPoint.id)).where(
            PlotPoint.project_id == project_id,
            PlotPoint.is_completed.is_(True),
        )
    )
    completed_count: int = completed_result.scalar_one()

    # 첫 번째 미완료 플롯 포인트 조회 (sequence_order 오름차순)
    current_result = await db.execute(
        select(PlotPoint)
        .where(
            PlotPoint.project_id == project_id,
            PlotPoint.is_completed.is_(False),
        )
        .order_by(PlotPoint.sequence_order.asc())
        .limit(1)
    )
    current_plot_point: PlotPoint | None = current_result.scalar_one_or_none()

    return CurrentPlotPositionResponse(
        current_plot_point=(
            PlotPointResponse.model_validate(current_plot_point)
            if current_plot_point is not None
            else None
        ),
        total_plot_points=total_count,
        completed_count=completed_count,
    )
