"""
컨텍스트 관리 서비스 (ContextManagerService)

StoryContext 캐싱/조회, 컨텍스트 윈도우 관리(토큰 카운팅·요약),
캐릭터 등장 추적 등 컨텍스트와 관련된 모든 비즈니스 로직을 담당합니다.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models.chapter import Chapter
from backend.app.models.character import Character
from backend.app.models.plot import PlotPoint
from backend.app.models.worldbuilding import WorldBuilding
from backend.app.schemas.character import CharacterResponse
from backend.app.schemas.plot import PlotPointResponse
from backend.app.schemas.story_context import StoryContext
from backend.app.schemas.worldbuilding import WorldBuildingResponse

logger = logging.getLogger(__name__)

# ─── 상수 ─────────────────────────────────────────────────────────────────────

CACHE_KEY_PREFIX = "story_context"
CACHE_TTL_SECONDS = 3600          # 1시간
MAX_CONTEXT_TOKENS = 100_000      # 컨텍스트 윈도우 최대 토큰 수
RECENT_CHAPTERS_LIMIT = 5         # 최근 챕터 요약에 포함할 챕터 수


# ─── 토큰 카운팅 유틸리티 ──────────────────────────────────────────────────────

try:
    import tiktoken
    _tiktoken_enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        """
        tiktoken을 사용해 텍스트의 토큰 수를 반환합니다.
        한국어를 포함한 다국어 텍스트에 적합합니다.
        """
        return len(_tiktoken_enc.encode(text))

except Exception:
    # tiktoken을 사용할 수 없는 경우 UTF-8 바이트 기반 근사치 사용
    def count_tokens(text: str) -> int:  # type: ignore[misc]
        """
        tiktoken 미사용 시 UTF-8 바이트 수 / 4 로 토큰 수를 근사합니다.
        한국어 문자는 UTF-8에서 3바이트이므로 실제 토큰 수와 유사합니다.
        """
        return len(text.encode("utf-8")) // 4


# ─── 데이터 구조 ───────────────────────────────────────────────────────────────

@dataclass
class CharacterTimelineEntry:
    """챕터별 캐릭터 등장 정보"""
    character_id: str
    character_name: str
    chapter_id: str
    chapter_number: int
    mention_count: int
    appearance_type: str          # "major" | "minor" | "mentioned"
    key_context: str              # 해당 챕터에서 캐릭터가 등장하는 주요 문맥


@dataclass
class CharacterTimeline:
    """캐릭터 전체 타임라인"""
    character_id: str
    character_name: str
    entries: List[CharacterTimelineEntry] = field(default_factory=list)
    total_appearances: int = 0


# ─── 예외 클래스 ───────────────────────────────────────────────────────────────

class ContextManagerError(Exception):
    """컨텍스트 관리 서비스 기본 예외"""
    pass


class ProjectNotFoundError(ContextManagerError):
    """프로젝트를 찾을 수 없을 때 발생하는 예외"""
    pass


# ─── 서비스 ────────────────────────────────────────────────────────────────────

class ContextManagerService:
    """
    StoryContext 저장/조회, 컨텍스트 윈도우 관리, 캐릭터 추적을 담당하는 서비스.

    모든 공개 메서드는 AsyncSession을 인자로 받아 트랜잭션 경계를 호출자가 제어할 수 있도록 합니다.
    Redis 캐시를 우선 조회하고, 캐시 미스 시 DB에서 데이터를 로드합니다.
    """

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    # ─── Redis 클라이언트 ──────────────────────────────────────────────────────

    def _get_redis(self) -> aioredis.Redis:
        """Redis 클라이언트 싱글턴을 반환합니다."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis

    @staticmethod
    def _cache_key(project_id: uuid.UUID) -> str:
        return f"{CACHE_KEY_PREFIX}:{project_id}"

    # ─── 6.1 StoryContext 저장 및 조회 ────────────────────────────────────────

    async def get_story_context(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> StoryContext:
        """
        프로젝트의 StoryContext를 반환합니다.

        Redis 캐시를 우선 조회하고, 캐시 미스 시 DB에서 데이터를 로드한 뒤
        캐시에 저장합니다. 캐시 히트율 80% 이상을 목표로 합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID

        Returns:
            StoryContext 객체

        Raises:
            ContextManagerError: DB 조회 실패 시
        """
        cache_key = self._cache_key(project_id)

        # 1) 캐시 조회
        try:
            redis = self._get_redis()
            cached = await redis.get(cache_key)
            if cached:
                logger.debug("StoryContext 캐시 히트: project_id=%s", project_id)
                data = json.loads(cached)
                return StoryContext(**data)
        except Exception as exc:
            # Redis 장애 시 DB 폴백 (fail-open)
            logger.warning("Redis 조회 실패, DB 폴백: %s", exc)

        # 2) DB 조회
        logger.debug("StoryContext 캐시 미스, DB 조회: project_id=%s", project_id)
        context = await self._build_context_from_db(db, project_id)

        # 3) 캐시 저장
        await self._set_cache(cache_key, context)

        return context

    async def update_context(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> StoryContext:
        """
        챕터 수정 등 변경 이벤트 발생 시 StoryContext를 갱신합니다.

        기존 캐시를 무효화하고 DB에서 최신 데이터를 로드한 뒤 캐시를 갱신합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID

        Returns:
            갱신된 StoryContext 객체

        Raises:
            ContextManagerError: DB 조회 실패 시
        """
        cache_key = self._cache_key(project_id)

        # 캐시 무효화
        try:
            redis = self._get_redis()
            await redis.delete(cache_key)
        except Exception as exc:
            logger.warning("캐시 무효화 실패: %s", exc)

        # DB에서 최신 컨텍스트 빌드
        context = await self._build_context_from_db(db, project_id)

        # 캐시 갱신
        await self._set_cache(cache_key, context)

        logger.info("StoryContext 갱신 완료: project_id=%s", project_id)
        return context

    # ─── 6.2 컨텍스트 윈도우 관리 ─────────────────────────────────────────────

    async def summarize_old_chapters(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapters: List[Chapter],
    ) -> str:
        """
        전체 챕터 컨텍스트가 MAX_CONTEXT_TOKENS를 초과할 경우,
        오래된 챕터들을 요약하여 토큰 수를 줄입니다.

        요약 시 다음 정보를 보존합니다:
        - 캐릭터 이름
        - 핵심 플롯 이벤트
        - 세계관 규칙 참조

        현재는 추출적 요약(첫 단락 + 마지막 단락)을 사용합니다.
        TODO: Qwen 클라이언트 구현 후 AI 기반 추상적 요약으로 교체

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID
            chapters: 요약 대상 챕터 목록 (오래된 순)

        Returns:
            요약된 텍스트 문자열
        """
        if not chapters:
            return ""

        # 전체 토큰 수 계산
        total_tokens = sum(count_tokens(ch.content) for ch in chapters)
        if total_tokens <= MAX_CONTEXT_TOKENS:
            # 토큰 한도 미초과 시 요약 불필요
            return "\n\n".join(
                f"[챕터 {ch.chapter_number}] {ch.title or ''}\n{ch.content}"
                for ch in chapters
            )

        # 캐릭터 이름 목록 조회 (보존 대상)
        character_names = await self._get_character_names(db, project_id)

        # 오래된 챕터부터 요약 대상 선정
        # 최근 RECENT_CHAPTERS_LIMIT개 챕터는 전문 보존
        sorted_chapters = sorted(chapters, key=lambda c: c.chapter_number)
        recent_chapters = sorted_chapters[-RECENT_CHAPTERS_LIMIT:]
        old_chapters = sorted_chapters[:-RECENT_CHAPTERS_LIMIT]

        summary_parts: List[str] = []

        # 오래된 챕터: 추출적 요약 (첫 단락 + 마지막 단락)
        # TODO: Qwen 클라이언트 구현 후 AI 기반 추상적 요약으로 교체
        for chapter in old_chapters:
            chapter_summary = self._extractive_summarize(
                chapter=chapter,
                character_names=character_names,
            )
            summary_parts.append(chapter_summary)

        # 최근 챕터: 전문 포함
        for chapter in recent_chapters:
            title_part = f" - {chapter.title}" if chapter.title else ""
            summary_parts.append(
                f"[챕터 {chapter.chapter_number}{title_part}]\n{chapter.content}"
            )

        return "\n\n---\n\n".join(summary_parts)

    def _extractive_summarize(
        self,
        chapter: Chapter,
        character_names: List[str],
    ) -> str:
        """
        챕터 내용에서 첫 단락과 마지막 단락을 추출하여 요약을 생성합니다.
        캐릭터 이름이 포함된 문장을 우선적으로 보존합니다.

        Args:
            chapter: 요약할 챕터
            character_names: 보존할 캐릭터 이름 목록

        Returns:
            추출적 요약 문자열
        """
        content = chapter.content.strip()
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        if not paragraphs:
            return f"[챕터 {chapter.chapter_number} 요약] (내용 없음)"

        title_part = f" - {chapter.title}" if chapter.title else ""
        header = f"[챕터 {chapter.chapter_number}{title_part} 요약]"

        if len(paragraphs) == 1:
            return f"{header}\n{paragraphs[0]}"

        # 첫 단락 + 마지막 단락
        first_para = paragraphs[0]
        last_para = paragraphs[-1]

        # 캐릭터 이름이 포함된 핵심 문장 추출
        key_sentences: List[str] = []
        if character_names:
            for para in paragraphs[1:-1]:
                sentences = [s.strip() for s in para.replace("。", ".").split(".") if s.strip()]
                for sentence in sentences:
                    if any(name in sentence for name in character_names):
                        key_sentences.append(sentence)
                        if len(key_sentences) >= 3:
                            break
                if len(key_sentences) >= 3:
                    break

        parts = [header, first_para]
        if key_sentences:
            parts.append("(핵심 장면: " + " / ".join(key_sentences) + ")")
        parts.append(last_para)

        return "\n".join(parts)

    # ─── 6.3 캐릭터 추적 ──────────────────────────────────────────────────────

    async def track_character_development(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        character_id: Optional[uuid.UUID] = None,
    ) -> List[CharacterTimeline]:
        """
        프로젝트 내 캐릭터의 챕터별 등장 및 변화를 추적합니다.

        각 챕터의 content에서 캐릭터 이름을 검색하여 등장 횟수를 파악하고,
        등장 유형(major/minor/mentioned)을 분류합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID
            character_id: 특정 캐릭터만 추적할 경우 해당 ID (None이면 전체)

        Returns:
            CharacterTimeline 목록

        Raises:
            ContextManagerError: DB 조회 실패 시
        """
        try:
            # 캐릭터 조회
            char_query = select(Character).where(
                Character.project_id == project_id
            )
            if character_id is not None:
                char_query = char_query.where(Character.id == character_id)

            char_result = await db.execute(char_query)
            characters = list(char_result.scalars().all())

            if not characters:
                return []

            # 챕터 조회 (오름차순)
            chapter_result = await db.execute(
                select(Chapter)
                .where(
                    Chapter.project_id == project_id,
                    Chapter.is_deleted.is_(False),
                )
                .order_by(Chapter.chapter_number.asc())
            )
            chapters = list(chapter_result.scalars().all())

            if not chapters:
                return []

            # 캐릭터별 타임라인 구성
            timelines: List[CharacterTimeline] = []

            for character in characters:
                timeline = CharacterTimeline(
                    character_id=str(character.id),
                    character_name=character.name,
                )

                for chapter in chapters:
                    entry = self._analyze_character_in_chapter(
                        character=character,
                        chapter=chapter,
                    )
                    if entry is not None:
                        timeline.entries.append(entry)
                        timeline.total_appearances += 1

                timelines.append(timeline)

            return timelines

        except Exception as exc:
            logger.error(
                "캐릭터 추적 실패: project_id=%s, error=%s",
                project_id,
                exc,
                exc_info=True,
            )
            raise ContextManagerError(f"캐릭터 추적 중 오류가 발생했습니다: {exc}") from exc

    def _analyze_character_in_chapter(
        self,
        character: Character,
        chapter: Chapter,
    ) -> Optional[CharacterTimelineEntry]:
        """
        챕터 내용에서 캐릭터 이름의 등장 횟수를 분석하고
        CharacterTimelineEntry를 반환합니다.

        등장 유형 기준:
        - major (주요): 5회 이상 언급
        - minor (조연): 2~4회 언급
        - mentioned (언급): 1회 언급

        Args:
            character: 분석할 캐릭터
            chapter: 분석할 챕터

        Returns:
            CharacterTimelineEntry 또는 None (등장하지 않는 경우)
        """
        content = chapter.content
        name = character.name

        # 이름 등장 횟수 계산 (단순 문자열 검색)
        mention_count = content.count(name)

        if mention_count == 0:
            return None

        # 등장 유형 분류
        if mention_count >= 5:
            appearance_type = "major"
        elif mention_count >= 2:
            appearance_type = "minor"
        else:
            appearance_type = "mentioned"

        # 캐릭터 이름 주변 문맥 추출 (첫 번째 등장 위치 기준)
        key_context = self._extract_context_around_name(content, name)

        return CharacterTimelineEntry(
            character_id=str(character.id),
            character_name=name,
            chapter_id=str(chapter.id),
            chapter_number=chapter.chapter_number,
            mention_count=mention_count,
            appearance_type=appearance_type,
            key_context=key_context,
        )

    @staticmethod
    def _extract_context_around_name(content: str, name: str, window: int = 100) -> str:
        """
        텍스트에서 이름 첫 등장 위치 주변 window 글자를 추출합니다.

        Args:
            content: 전체 텍스트
            name: 검색할 이름
            window: 이름 앞뒤로 추출할 글자 수

        Returns:
            추출된 문맥 문자열
        """
        idx = content.find(name)
        if idx == -1:
            return ""

        start = max(0, idx - window)
        end = min(len(content), idx + len(name) + window)
        excerpt = content[start:end].strip()

        # 앞뒤 말줄임표 추가
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."

        return excerpt

    # ─── 내부 헬퍼 메서드 ─────────────────────────────────────────────────────

    async def _build_context_from_db(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> StoryContext:
        """
        DB에서 프로젝트 데이터를 조회하여 StoryContext를 구성합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID

        Returns:
            StoryContext 객체

        Raises:
            ContextManagerError: DB 조회 실패 시
        """
        try:
            # 캐릭터 조회
            char_result = await db.execute(
                select(Character).where(Character.project_id == project_id)
            )
            characters = list(char_result.scalars().all())

            # 플롯 포인트 조회 (순서 오름차순)
            plot_result = await db.execute(
                select(PlotPoint)
                .where(PlotPoint.project_id == project_id)
                .order_by(PlotPoint.sequence_order.asc())
            )
            plot_points = list(plot_result.scalars().all())

            # 세계관 조회
            wb_result = await db.execute(
                select(WorldBuilding).where(WorldBuilding.project_id == project_id)
            )
            world_buildings = list(wb_result.scalars().all())

            # 최근 챕터 조회 (최신 RECENT_CHAPTERS_LIMIT개)
            chapter_result = await db.execute(
                select(Chapter)
                .where(
                    Chapter.project_id == project_id,
                    Chapter.is_deleted.is_(False),
                )
                .order_by(Chapter.chapter_number.desc())
                .limit(RECENT_CHAPTERS_LIMIT)
            )
            recent_chapters = list(chapter_result.scalars().all())
            # 오름차순으로 재정렬
            recent_chapters.sort(key=lambda c: c.chapter_number)

            # 최근 챕터 요약 생성
            recent_summary = self._build_recent_chapters_summary(recent_chapters)

            # 전체 토큰 수 계산
            total_tokens = self._calculate_total_tokens(
                characters=characters,
                plot_points=plot_points,
                world_buildings=world_buildings,
                recent_summary=recent_summary,
            )

            # Pydantic 스키마로 변환
            character_responses = [
                CharacterResponse.model_validate(c) for c in characters
            ]
            plot_responses = [
                PlotPointResponse.model_validate(p) for p in plot_points
            ]
            wb_responses = [
                WorldBuildingResponse.model_validate(w) for w in world_buildings
            ]

            return StoryContext(
                project_id=str(project_id),
                characters=character_responses,
                plot_points=plot_responses,
                world_building=wb_responses,
                recent_chapters_summary=recent_summary,
                total_tokens=total_tokens,
                last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
            )

        except Exception as exc:
            logger.error(
                "StoryContext DB 빌드 실패: project_id=%s, error=%s",
                project_id,
                exc,
                exc_info=True,
            )
            raise ContextManagerError(
                f"StoryContext 구성 중 오류가 발생했습니다: {exc}"
            ) from exc

    def _build_recent_chapters_summary(self, chapters: List[Chapter]) -> str:
        """
        최근 챕터 목록으로부터 요약 문자열을 생성합니다.

        Args:
            chapters: 최근 챕터 목록 (오름차순)

        Returns:
            요약 문자열
        """
        if not chapters:
            return ""

        parts: List[str] = []
        for chapter in chapters:
            title_part = f" - {chapter.title}" if chapter.title else ""
            # 챕터 내용의 첫 200자를 미리보기로 사용
            preview = chapter.content[:200].strip()
            if len(chapter.content) > 200:
                preview += "..."
            parts.append(f"챕터 {chapter.chapter_number}{title_part}: {preview}")

        return "\n".join(parts)

    def _calculate_total_tokens(
        self,
        characters: list,
        plot_points: list,
        world_buildings: list,
        recent_summary: str,
    ) -> int:
        """
        StoryContext 구성 요소들의 총 토큰 수를 계산합니다.

        Args:
            characters: 캐릭터 목록
            plot_points: 플롯 포인트 목록
            world_buildings: 세계관 목록
            recent_summary: 최근 챕터 요약 문자열

        Returns:
            총 토큰 수
        """
        total = 0

        for char in characters:
            text = f"{char.name} {char.appearance or ''} {char.background or ''}"
            total += count_tokens(text)

        for plot in plot_points:
            text = f"{plot.title} {plot.description or ''}"
            total += count_tokens(text)

        for wb in world_buildings:
            text = f"{wb.name} {wb.description}"
            total += count_tokens(text)

        total += count_tokens(recent_summary)

        return total

    async def _get_character_names(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
    ) -> List[str]:
        """
        프로젝트의 모든 캐릭터 이름 목록을 반환합니다.

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID

        Returns:
            캐릭터 이름 목록
        """
        try:
            result = await db.execute(
                select(Character.name).where(Character.project_id == project_id)
            )
            return [row[0] for row in result.all()]
        except Exception as exc:
            logger.warning("캐릭터 이름 조회 실패: %s", exc)
            return []

    async def _set_cache(self, cache_key: str, context: StoryContext) -> None:
        """
        StoryContext를 Redis에 직렬화하여 저장합니다.

        Args:
            cache_key: Redis 키
            context: 저장할 StoryContext
        """
        try:
            redis = self._get_redis()
            serialized = context.model_dump_json()
            await redis.setex(cache_key, CACHE_TTL_SECONDS, serialized)
            logger.debug("StoryContext 캐시 저장: key=%s", cache_key)
        except Exception as exc:
            # 캐시 저장 실패는 치명적이지 않으므로 경고만 기록
            logger.warning("StoryContext 캐시 저장 실패: %s", exc)


# 싱글턴 인스턴스 (의존성 주입용)
context_manager = ContextManagerService()
