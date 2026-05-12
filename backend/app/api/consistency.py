"""
일관성 검증 API 엔드포인트

- GET /api/chapters/{chapter_id}/consistency       챕터 일관성 검증
- GET /api/projects/{project_id}/consistency       프로젝트 전체 일관성 검증
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.chapter import Chapter
from backend.app.models.consistency import ConsistencyIssue
from backend.app.models.project import Project
from backend.app.schemas.consistency import ConsistencyIssueResponse, ConsistencyReport
from backend.app.services.consistency_checker import (
    ConsistencyCheckerService,
    consistency_checker,
)

router = APIRouter(tags=["일관성 검증"])


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


async def _get_chapter_or_404(
    db: AsyncSession,
    chapter_id: uuid.UUID,
) -> Chapter:
    """챕터를 조회하고 없으면 404를 반환합니다."""
    result = await db.execute(
        select(Chapter).where(
            Chapter.id == chapter_id,
            Chapter.is_deleted.is_(False),
        )
    )
    chapter: Chapter | None = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="챕터를 찾을 수 없습니다.",
        )
    return chapter


# ─── 챕터 일관성 검증 ─────────────────────────────────────────────────────────


@router.get(
    "/chapters/{chapter_id}/consistency",
    response_model=ConsistencyReport,
    summary="챕터 일관성 검증",
)
async def check_chapter_consistency(
    chapter_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    service: ConsistencyCheckerService = Depends(lambda: consistency_checker),
) -> ConsistencyReport:
    """
    챕터의 일관성을 검증하고 리포트를 반환합니다.
    
    캐릭터, 플롯, 세계관 요소를 검증하여:
    - 일관성 점수 (0-100)
    - 발견된 이슈 목록 (심각도, 설명, 줄번호 포함)
    
    를 반환합니다.
    
    - 403: 챕터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 챕터가 존재하지 않는 경우
    """
    # 챕터 조회
    chapter = await _get_chapter_or_404(db, chapter_id)
    
    # 프로젝트 소유자 확인
    project = await _get_project_or_404(db, chapter.project_id)
    _verify_project_owner(project, current_user.id)
    
    # 일관성 검증 수행
    try:
        score, issues = await service.check_chapter_consistency(db, chapter_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # 응답 생성
    issue_responses = [
        ConsistencyIssueResponse.model_validate(issue) for issue in issues
    ]
    
    return ConsistencyReport(
        chapter_id=chapter_id,
        score=score,
        issues=issue_responses,
        checked_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )


# ─── 프로젝트 전체 일관성 검증 ────────────────────────────────────────────────


@router.get(
    "/projects/{project_id}/consistency",
    response_model=dict,
    summary="프로젝트 전체 일관성 검증",
)
async def check_project_consistency(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    service: ConsistencyCheckerService = Depends(lambda: consistency_checker),
) -> dict:
    """
    프로젝트의 모든 챕터에 대해 일관성을 검증합니다.
    
    각 챕터별 일관성 점수와 이슈를 반환하며,
    프로젝트 전체의 평균 일관성 점수도 함께 제공합니다.
    
    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    # 프로젝트 소유자 확인
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)
    
    # 프로젝트의 모든 활성 챕터 조회
    result = await db.execute(
        select(Chapter)
        .where(
            Chapter.project_id == project_id,
            Chapter.is_deleted.is_(False),
        )
        .order_by(Chapter.chapter_number.asc())
    )
    chapters = list(result.scalars().all())
    
    if not chapters:
        return {
            "project_id": str(project_id),
            "average_score": 100,
            "total_chapters": 0,
            "chapters": [],
            "checked_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }
    
    # 각 챕터별 일관성 검증
    chapter_reports = []
    total_score = 0
    
    for chapter in chapters:
        try:
            score, issues = await service.check_chapter_consistency(db, chapter.id)
            
            issue_responses = [
                ConsistencyIssueResponse.model_validate(issue) for issue in issues
            ]
            
            chapter_reports.append({
                "chapter_id": str(chapter.id),
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "score": score,
                "issue_count": len(issues),
                "issues": [issue.model_dump() for issue in issue_responses],
            })
            
            total_score += score
            
        except ValueError:
            # 챕터 검증 실패 시 건너뛰기
            continue
    
    # 평균 점수 계산
    average_score = total_score // len(chapter_reports) if chapter_reports else 100
    
    return {
        "project_id": str(project_id),
        "average_score": average_score,
        "total_chapters": len(chapter_reports),
        "chapters": chapter_reports,
        "checked_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }
