"""
챕터 관리 서비스 (ChapterManagerService)

챕터 CRUD, 버전 관리, 순서 변경 등 챕터와 관련된 모든 비즈니스 로직을 담당합니다.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.chapter import Chapter, ChapterVersion
from backend.app.models.project import Project
from backend.app.schemas.chapter import ChapterCreate, ChapterUpdate

# 챕터 버전 최대 보관 수
MAX_CHAPTER_VERSIONS = 5


class ChapterNotFoundError(Exception):
    """챕터를 찾을 수 없을 때 발생하는 예외"""
    pass


class ChapterVersionNotFoundError(Exception):
    """챕터 버전을 찾을 수 없을 때 발생하는 예외"""
    pass


class ChapterNumberConflictError(Exception):
    """챕터 번호 충돌 시 발생하는 예외"""
    pass


class ChapterManagerService:
    """
    챕터 생성, 조회, 수정, 삭제 및 버전 관리를 담당하는 서비스.

    모든 메서드는 AsyncSession을 인자로 받아 트랜잭션 경계를 호출자가 제어할 수 있도록 합니다.
    """

    # ─── 챕터 CRUD ────────────────────────────────────────────────────────────

    async def create_chapter(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        data: ChapterCreate,
    ) -> Chapter:
        """
        새 챕터를 생성합니다.

        chapter_number가 지정되지 않으면 현재 최대 챕터 번호 + 1로 자동 설정됩니다.
        지정된 경우 해당 번호가 이미 존재하면 ChapterNumberConflictError를 발생시킵니다.

        Args:
            db: 비동기 DB 세션
            project_id: 챕터가 속할 프로젝트 ID
            data: 챕터 생성 데이터

        Returns:
            생성된 Chapter ORM 객체

        Raises:
            ChapterNumberConflictError: 챕터 번호가 이미 존재하는 경우
        """
        # 챕터 번호 결정
        chapter_number = data.chapter_number
        if chapter_number is None:
            chapter_number = await self._next_chapter_number(db, project_id)
        else:
            # 중복 확인
            existing = await self._get_chapter_by_number(db, project_id, chapter_number)
            if existing is not None:
                raise ChapterNumberConflictError(
                    f"챕터 번호 {chapter_number}이(가) 이미 존재합니다."
                )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        word_count = data.word_count if data.word_count is not None else len(data.content)

        chapter = Chapter(
            id=uuid.uuid4(),
            project_id=project_id,
            chapter_number=chapter_number,
            title=data.title,
            content=data.content,
            word_count=word_count,
            consistency_score=None,
            created_at=now,
            updated_at=now,
            is_deleted=False,
        )
        db.add(chapter)
        await db.flush()

        # 프로젝트 총 글자 수 업데이트
        await self._update_project_word_count(db, project_id)

        return chapter

    async def get_chapter(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
    ) -> Chapter:
        """
        챕터 ID로 챕터를 조회합니다.

        Args:
            db: 비동기 DB 세션
            chapter_id: 조회할 챕터 ID

        Returns:
            Chapter ORM 객체

        Raises:
            ChapterNotFoundError: 챕터가 존재하지 않거나 삭제된 경우
        """
        result = await db.execute(
            select(Chapter).where(
                Chapter.id == chapter_id,
                Chapter.is_deleted.is_(False),
            )
        )
        chapter = result.scalar_one_or_none()
        if chapter is None:
            raise ChapterNotFoundError(f"챕터를 찾을 수 없습니다: {chapter_id}")
        return chapter

    async def get_chapters_by_project(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[Chapter]:
        """
        프로젝트의 모든 챕터를 챕터 번호 오름차순으로 반환합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID

        Returns:
            Chapter 목록 (chapter_number 오름차순)
        """
        result = await db.execute(
            select(Chapter)
            .where(
                Chapter.project_id == project_id,
                Chapter.is_deleted.is_(False),
            )
            .order_by(Chapter.chapter_number.asc())
        )
        return list(result.scalars().all())

    async def update_chapter(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
        data: ChapterUpdate,
    ) -> Chapter:
        """
        챕터를 수정합니다. 수정 전 현재 내용을 버전으로 자동 저장합니다.

        content가 변경되는 경우에만 버전이 생성됩니다.
        버전은 최대 MAX_CHAPTER_VERSIONS(5)개까지 유지되며, 초과 시 가장 오래된 버전이 삭제됩니다.

        Args:
            db: 비동기 DB 세션
            chapter_id: 수정할 챕터 ID
            data: 수정 데이터 (제공된 필드만 업데이트)

        Returns:
            수정된 Chapter ORM 객체

        Raises:
            ChapterNotFoundError: 챕터가 존재하지 않는 경우
        """
        chapter = await self.get_chapter(db, chapter_id)

        update_data = data.model_dump(exclude_unset=True)

        # content가 변경되는 경우 현재 버전을 저장
        if "content" in update_data and update_data["content"] != chapter.content:
            await self._save_version(db, chapter)

        # 필드 업데이트
        for field, value in update_data.items():
            setattr(chapter, field, value)

        # word_count 자동 계산 (content만 변경되고 word_count가 명시되지 않은 경우)
        if "content" in update_data and "word_count" not in update_data:
            chapter.word_count = len(chapter.content)

        chapter.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()

        # 프로젝트 총 글자 수 업데이트
        await self._update_project_word_count(db, chapter.project_id)

        return chapter

    async def delete_chapter(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
    ) -> None:
        """
        챕터를 소프트 삭제합니다 (is_deleted = True).

        Args:
            db: 비동기 DB 세션
            chapter_id: 삭제할 챕터 ID

        Raises:
            ChapterNotFoundError: 챕터가 존재하지 않는 경우
        """
        chapter = await self.get_chapter(db, chapter_id)
        chapter.is_deleted = True
        chapter.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()

        # 프로젝트 총 글자 수 업데이트
        await self._update_project_word_count(db, chapter.project_id)

    # ─── 버전 관리 ────────────────────────────────────────────────────────────

    async def get_chapter_versions(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
        limit: int = MAX_CHAPTER_VERSIONS,
    ) -> List[ChapterVersion]:
        """
        챕터의 버전 히스토리를 최신순으로 반환합니다.

        Args:
            db: 비동기 DB 세션
            chapter_id: 챕터 ID
            limit: 반환할 최대 버전 수 (기본값: 5)

        Returns:
            ChapterVersion 목록 (version_number 내림차순)

        Raises:
            ChapterNotFoundError: 챕터가 존재하지 않는 경우
        """
        # 챕터 존재 확인
        await self.get_chapter(db, chapter_id)

        result = await db.execute(
            select(ChapterVersion)
            .where(ChapterVersion.chapter_id == chapter_id)
            .order_by(ChapterVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def rollback_to_version(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
        version_number: int,
    ) -> Chapter:
        """
        챕터를 특정 버전으로 롤백합니다.

        롤백 전 현재 내용을 새 버전으로 저장한 뒤, 지정된 버전의 내용으로 챕터를 복원합니다.

        Args:
            db: 비동기 DB 세션
            chapter_id: 챕터 ID
            version_number: 롤백할 버전 번호

        Returns:
            롤백된 Chapter ORM 객체

        Raises:
            ChapterNotFoundError: 챕터가 존재하지 않는 경우
            ChapterVersionNotFoundError: 지정된 버전이 존재하지 않는 경우
        """
        chapter = await self.get_chapter(db, chapter_id)

        # 대상 버전 조회
        result = await db.execute(
            select(ChapterVersion).where(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.version_number == version_number,
            )
        )
        target_version = result.scalar_one_or_none()
        if target_version is None:
            raise ChapterVersionNotFoundError(
                f"버전 {version_number}을(를) 찾을 수 없습니다."
            )

        # 현재 내용을 새 버전으로 저장
        await self._save_version(db, chapter)

        # 버전 내용으로 복원
        chapter.content = target_version.content
        chapter.word_count = target_version.word_count
        chapter.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.flush()

        return chapter

    # ─── 챕터 순서 변경 ───────────────────────────────────────────────────────

    async def reorder_chapters(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_ids: List[uuid.UUID],
    ) -> List[Chapter]:
        """
        챕터 순서를 재정렬합니다.

        chapter_ids 리스트의 순서대로 챕터 번호를 1부터 연속적으로 재할당합니다.
        리스트에 포함된 챕터 ID는 해당 프로젝트의 모든 활성 챕터와 일치해야 합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID
            chapter_ids: 새 순서로 정렬된 챕터 ID 목록

        Returns:
            재정렬된 Chapter 목록 (chapter_number 오름차순)

        Raises:
            ValueError: chapter_ids가 프로젝트의 챕터 목록과 일치하지 않는 경우
        """
        # 현재 활성 챕터 조회
        existing_chapters = await self.get_chapters_by_project(db, project_id)
        existing_ids = {ch.id for ch in existing_chapters}
        requested_ids = set(chapter_ids)

        if existing_ids != requested_ids:
            missing = existing_ids - requested_ids
            extra = requested_ids - existing_ids
            details = []
            if missing:
                details.append(f"누락된 챕터: {missing}")
            if extra:
                details.append(f"존재하지 않는 챕터: {extra}")
            raise ValueError(
                f"챕터 ID 목록이 프로젝트의 챕터와 일치하지 않습니다. {'; '.join(details)}"
            )

        # 챕터 맵 구성
        chapter_map = {ch.id: ch for ch in existing_chapters}

        # 임시 번호로 먼저 업데이트 (unique constraint 충돌 방지)
        # 음수 임시 번호 사용
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for i, chapter_id in enumerate(chapter_ids):
            chapter_map[chapter_id].chapter_number = -(i + 1)
            chapter_map[chapter_id].updated_at = now
        await db.flush()

        # 최종 번호 할당 (1부터 연속)
        for i, chapter_id in enumerate(chapter_ids):
            chapter_map[chapter_id].chapter_number = i + 1
        await db.flush()

        # 정렬된 목록 반환
        return [chapter_map[cid] for cid in chapter_ids]

    # ─── 내부 헬퍼 메서드 ─────────────────────────────────────────────────────

    async def _next_chapter_number(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> int:
        """프로젝트의 다음 챕터 번호를 반환합니다 (현재 최대 + 1)."""
        result = await db.execute(
            select(func.max(Chapter.chapter_number)).where(
                Chapter.project_id == project_id,
                Chapter.is_deleted.is_(False),
            )
        )
        max_number: Optional[int] = result.scalar_one_or_none()
        return (max_number or 0) + 1

    async def _get_chapter_by_number(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
    ) -> Optional[Chapter]:
        """챕터 번호로 챕터를 조회합니다 (삭제된 챕터 제외)."""
        result = await db.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_number == chapter_number,
                Chapter.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def _save_version(
        self,
        db: AsyncSession,
        chapter: Chapter,
    ) -> ChapterVersion:
        """
        챕터의 현재 내용을 새 버전으로 저장합니다.

        버전이 MAX_CHAPTER_VERSIONS를 초과하면 가장 오래된 버전을 삭제합니다.
        """
        # 현재 최대 버전 번호 조회
        result = await db.execute(
            select(func.max(ChapterVersion.version_number)).where(
                ChapterVersion.chapter_id == chapter.id
            )
        )
        max_version: Optional[int] = result.scalar_one_or_none()
        next_version_number = (max_version or 0) + 1

        # 새 버전 생성
        version = ChapterVersion(
            id=uuid.uuid4(),
            chapter_id=chapter.id,
            version_number=next_version_number,
            content=chapter.content,
            word_count=chapter.word_count,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(version)
        await db.flush()

        # 최대 버전 수 초과 시 가장 오래된 버전 삭제
        await self._prune_old_versions(db, chapter.id)

        return version

    async def _prune_old_versions(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
    ) -> None:
        """
        챕터 버전이 MAX_CHAPTER_VERSIONS를 초과하면 가장 오래된 버전을 삭제합니다.
        """
        # 보관할 최신 버전 ID 조회
        keep_result = await db.execute(
            select(ChapterVersion.id)
            .where(ChapterVersion.chapter_id == chapter_id)
            .order_by(ChapterVersion.version_number.desc())
            .limit(MAX_CHAPTER_VERSIONS)
        )
        keep_ids = [row[0] for row in keep_result.all()]

        if not keep_ids:
            return

        # 보관 목록에 없는 버전 삭제
        await db.execute(
            delete(ChapterVersion).where(
                ChapterVersion.chapter_id == chapter_id,
                ChapterVersion.id.not_in(keep_ids),
            )
        )

    async def _update_project_word_count(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> None:
        """프로젝트의 총 글자 수를 활성 챕터의 합계로 업데이트합니다."""
        result = await db.execute(
            select(func.coalesce(func.sum(Chapter.word_count), 0)).where(
                Chapter.project_id == project_id,
                Chapter.is_deleted.is_(False),
            )
        )
        total: int = result.scalar_one()

        await db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(
                total_word_count=total,
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )


# 싱글턴 인스턴스 (의존성 주입용)
chapter_manager = ChapterManagerService()
