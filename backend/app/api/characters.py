"""
캐릭터 관리 API 엔드포인트

- POST   /api/projects/{project_id}/characters   캐릭터 생성
- GET    /api/projects/{project_id}/characters   캐릭터 목록 조회
- PUT    /api/characters/{character_id}          캐릭터 수정
- DELETE /api/characters/{character_id}          캐릭터 삭제
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import CurrentUser
from backend.app.database import get_db
from backend.app.models.character import Character
from backend.app.models.project import Project
from backend.app.schemas.character import (
    CharacterCreate,
    CharacterListResponse,
    CharacterResponse,
    CharacterUpdate,
)
from backend.app.services.context_manager import context_manager

router = APIRouter(tags=["캐릭터 관리"])


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


async def _get_character_or_404(
    db: AsyncSession,
    character_id: uuid.UUID,
) -> Character:
    """캐릭터를 조회하고 없으면 404를 반환합니다."""
    result = await db.execute(
        select(Character).where(Character.id == character_id)
    )
    character: Character | None = result.scalar_one_or_none()
    if character is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="캐릭터를 찾을 수 없습니다.",
        )
    return character


async def _get_character_and_verify_owner(
    db: AsyncSession,
    character_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> Character:
    """캐릭터를 조회하고 프로젝트 소유자를 검증합니다."""
    character = await _get_character_or_404(db, character_id)
    project = await _get_project_or_404(db, character.project_id)
    _verify_project_owner(project, current_user_id)
    return character


# ─── 프로젝트 하위 캐릭터 엔드포인트 ─────────────────────────────────────────


@router.post(
    "/projects/{project_id}/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="캐릭터 생성",
)
async def create_character(
    project_id: uuid.UUID,
    body: CharacterCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CharacterResponse:
    """
    프로젝트에 새 캐릭터를 생성합니다.

    캐릭터 생성 후 프로젝트의 StoryContext가 자동으로 갱신됩니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    character = Character(
        id=uuid.uuid4(),
        project_id=project_id,
        name=body.name,
        age=body.age,
        personality_traits=body.personality_traits or [],
        appearance=body.appearance,
        background=body.background,
        relationships=body.relationships or {},
        created_at=now,
        updated_at=now,
    )
    db.add(character)
    await db.flush()

    # StoryContext 자동 갱신 (7.2 캐릭터 프로필 StoryContext 연동)
    await context_manager.update_context(db, project_id)

    return CharacterResponse.model_validate(character)


@router.get(
    "/projects/{project_id}/characters",
    response_model=CharacterListResponse,
    summary="캐릭터 목록 조회",
)
async def list_characters(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CharacterListResponse:
    """
    프로젝트의 모든 캐릭터를 생성일 오름차순으로 반환합니다.

    - 403: 프로젝트 소유자가 아닌 경우
    - 404: 프로젝트가 존재하지 않는 경우
    """
    project = await _get_project_or_404(db, project_id)
    _verify_project_owner(project, current_user.id)

    result = await db.execute(
        select(Character)
        .where(Character.project_id == project_id)
        .order_by(Character.created_at.asc())
    )
    characters = list(result.scalars().all())

    items = [CharacterResponse.model_validate(c) for c in characters]
    return CharacterListResponse(items=items, total=len(items))


# ─── 캐릭터 단일 엔드포인트 ──────────────────────────────────────────────────


@router.put(
    "/characters/{character_id}",
    response_model=CharacterResponse,
    summary="캐릭터 수정",
)
async def update_character(
    character_id: uuid.UUID,
    body: CharacterUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CharacterResponse:
    """
    캐릭터 정보를 부분 업데이트합니다.

    제공된 필드만 업데이트됩니다 (partial update).
    수정 후 프로젝트의 StoryContext가 자동으로 갱신됩니다.

    - 403: 캐릭터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 캐릭터가 존재하지 않는 경우
    """
    character = await _get_character_and_verify_owner(db, character_id, current_user.id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(character, field, value)

    character.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.flush()

    # StoryContext 자동 갱신 (7.2 캐릭터 프로필 StoryContext 연동)
    await context_manager.update_context(db, character.project_id)

    return CharacterResponse.model_validate(character)


@router.delete(
    "/characters/{character_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="캐릭터 삭제",
)
async def delete_character(
    character_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    캐릭터를 삭제합니다.

    삭제 후 프로젝트의 StoryContext가 자동으로 갱신됩니다.

    - 성공 시 204 No Content 반환
    - 403: 캐릭터가 속한 프로젝트의 소유자가 아닌 경우
    - 404: 캐릭터가 존재하지 않는 경우
    """
    character = await _get_character_and_verify_owner(db, character_id, current_user.id)
    project_id = character.project_id

    await db.delete(character)
    await db.flush()

    # StoryContext 자동 갱신 (7.2 캐릭터 프로필 StoryContext 연동)
    await context_manager.update_context(db, project_id)
