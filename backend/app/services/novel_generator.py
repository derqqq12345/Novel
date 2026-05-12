"""
Novel Generator Service

챕터 생성 파이프라인: ContextManager → RAG → Qwen → ChapterManager
프롬프트 엔지니어링, 챕터 생성, 재생성 로직을 담당합니다.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.generation_log import GenerationLog
from backend.app.schemas.chapter import ChapterCreate, ChapterUpdate
from backend.app.schemas.generation import GenerationParameters, Genre, Tone, UserFeedback
from backend.app.schemas.story_context import StoryContext
from backend.app.services.chapter_manager import chapter_manager
from backend.app.services.context_manager import context_manager
from backend.app.services.qwen_client import AIModelResponse, qwen_client
from backend.app.services.rag_system import RelevantPassage, rag_system

logger = logging.getLogger(__name__)

# ─── 상수 ─────────────────────────────────────────────────────────────────────

MIN_CHAPTER_LENGTH = 2000  # 최소 한국어 글자 수
MAX_TOKENS_RETRY = 8000    # 재시도 시 최대 토큰 수

# 장르 한국어 매핑
GENRE_KO_MAP = {
    Genre.FANTASY: "판타지",
    Genre.ROMANCE: "로맨스",
    Genre.MYSTERY: "미스터리",
    Genre.SCIENCE_FICTION: "SF 공상과학",
    Genre.THRILLER: "스릴러",
}

# 톤 한국어 매핑
TONE_KO_MAP = {
    Tone.SERIOUS: "진지하고 문학적인",
    Tone.HUMOROUS: "유머러스하고 가벼운",
    Tone.DARK: "어둡고 긴장감 있는",
    Tone.LIGHTHEARTED: "밝고 따뜻한",
}


# ─── 예외 클래스 ───────────────────────────────────────────────────────────────

class NovelGeneratorError(Exception):
    """Novel Generator 서비스 기본 예외"""
    pass



# ─── 서비스 ────────────────────────────────────────────────────────────────────

class NovelGeneratorService:
    """
    AI 기반 챕터 생성 서비스.

    ContextManager → RAG → Qwen → ChapterManager 파이프라인으로
    한국어 장편소설 챕터를 생성하고 저장합니다.

    사용 예시:
        service = NovelGeneratorService()
        chapter = await service.generate_chapter(db, project_id, 1, parameters, user_id)
    """

    # ─── 12.1 프롬프트 엔지니어링 ─────────────────────────────────────────────

    def _build_prompt(
        self,
        story_context: StoryContext,
        relevant_passages: List[RelevantPassage],
        parameters: GenerationParameters,
        chapter_number: int,
        user_prompt: Optional[str] = None,
        feedback: Optional[UserFeedback] = None,
    ) -> str:
        """
        Qwen 모델에 전달할 전체 프롬프트를 구성합니다.

        한국어 장편소설 특화 시스템 프롬프트와 함께
        캐릭터 프로필, 플롯 위치, 세계관 규칙, RAG 컨텍스트를 포함합니다.

        Args:
            story_context: 현재 스토리 컨텍스트 (캐릭터, 플롯, 세계관)
            relevant_passages: RAG로 검색된 관련 이전 구절
            parameters: 생성 파라미터 (장르, 톤, 토큰 수 등)
            chapter_number: 생성할 챕터 번호
            user_prompt: 사용자 지정 프롬프트 (선택)
            feedback: 재생성 시 사용자 피드백 (선택)

        Returns:
            완성된 프롬프트 문자열
        """
        genre_ko = GENRE_KO_MAP.get(parameters.genre, parameters.genre.value)
        tone_ko = TONE_KO_MAP.get(parameters.tone, parameters.tone.value)

        sections: List[str] = []

        # ── 시스템 역할 및 기본 지시사항 ──────────────────────────────────────
        sections.append(
            f"당신은 한국어 장편소설 전문 작가입니다. "
            f"장르는 {genre_ko}이며, 문체는 {tone_ko} 스타일로 작성합니다.\n"
            f"지금부터 소설의 {chapter_number}번째 챕터를 작성합니다."
        )

        # ── 캐릭터 프로필 ──────────────────────────────────────────────────────
        if story_context.characters:
            char_lines: List[str] = []
            for char in story_context.characters:
                traits = ", ".join(char.personality_traits or [])
                relationships_str = ""
                if char.relationships:
                    rel_parts = [f"{k}: {v}" for k, v in char.relationships.items()]
                    relationships_str = f"\n  - 관계: {', '.join(rel_parts)}"

                char_desc = (
                    f"- {char.name}"
                    + (f" (나이: {char.age})" if char.age is not None else "")
                    + (f"\n  - 성격: {traits}" if traits else "")
                    + (f"\n  - 외모: {char.appearance}" if char.appearance else "")
                    + (f"\n  - 배경: {char.background}" if char.background else "")
                    + relationships_str
                )
                char_lines.append(char_desc)

            sections.append("[등장인물 프로필]\n" + "\n".join(char_lines))

        # ── 현재 플롯 위치 ─────────────────────────────────────────────────────
        current_plot = None
        for pp in story_context.plot_points:
            if not pp.is_completed:
                current_plot = pp
                break

        if current_plot:
            plot_stage_ko = {
                "exposition": "발단",
                "rising_action": "전개",
                "climax": "절정",
                "falling_action": "하강",
                "resolution": "결말",
            }.get(current_plot.plot_stage or "", current_plot.plot_stage or "")

            plot_info = (
                f"[현재 플롯 위치]\n"
                f"- 단계: {plot_stage_ko}\n"
                f"- 플롯 포인트: {current_plot.title}\n"
            )
            if current_plot.description:
                plot_info += f"- 설명: {current_plot.description}\n"
            if current_plot.target_chapter:
                plot_info += f"- 목표 챕터: {current_plot.target_chapter}챕터\n"
            sections.append(plot_info.rstrip())
        elif story_context.plot_points:
            # 모든 플롯이 완료된 경우
            sections.append("[현재 플롯 위치]\n- 모든 주요 플롯 포인트가 완료되었습니다. 결말을 향해 나아가세요.")

        # ── 세계관 규칙 ────────────────────────────────────────────────────────
        if story_context.world_building:
            # 카테고리별 그룹화
            wb_by_category: dict = {}
            for wb in story_context.world_building:
                cat = wb.category
                if cat not in wb_by_category:
                    wb_by_category[cat] = []
                wb_by_category[cat].append(wb)

            wb_lines: List[str] = ["[세계관 설정]"]
            for category, items in wb_by_category.items():
                wb_lines.append(f"\n[{category}]")
                for item in items:
                    item_desc = f"- {item.name}: {item.description}"
                    if item.rules:
                        rules_str = "; ".join(
                            f"{k}: {v}" for k, v in item.rules.items()
                        )
                        item_desc += f"\n  규칙: {rules_str}"
                    wb_lines.append(item_desc)

            sections.append("\n".join(wb_lines))

        # ── RAG 컨텍스트 (관련 이전 구절) ─────────────────────────────────────
        if relevant_passages:
            rag_context = rag_system.build_rag_context(relevant_passages)
            if rag_context:
                sections.append(rag_context)

        # ── 최근 챕터 요약 ─────────────────────────────────────────────────────
        if story_context.recent_chapters_summary:
            sections.append(
                "[최근 챕터 요약]\n" + story_context.recent_chapters_summary
            )

        # ── 재생성 피드백 지시사항 ─────────────────────────────────────────────
        if feedback:
            feedback_lines: List[str] = ["[재생성 지시사항]"]
            if feedback.tone_adjustment:
                feedback_lines.append(f"- 톤 조정: {feedback.tone_adjustment}")
            if feedback.plot_direction:
                feedback_lines.append(f"- 플롯 방향: {feedback.plot_direction}")
            if feedback.custom_instructions:
                feedback_lines.append(f"- 추가 지시사항: {feedback.custom_instructions}")
            if len(feedback_lines) > 1:
                sections.append("\n".join(feedback_lines))

        # ── 사용자 지정 프롬프트 ───────────────────────────────────────────────
        if user_prompt:
            sections.append(f"[작가 지시사항]\n{user_prompt}")

        # ── 최종 생성 지시사항 ─────────────────────────────────────────────────
        sections.append(
            f"[생성 지시사항]\n"
            f"위의 모든 정보를 바탕으로 {chapter_number}번째 챕터를 작성하세요.\n"
            f"- 장르: {genre_ko}\n"
            f"- 문체: {tone_ko}\n"
            f"- 최소 2,000자 이상의 한국어 산문으로 작성하세요.\n"
            f"- 챕터 제목은 포함하지 마세요. 본문만 작성하세요.\n"
            f"- 자연스러운 한국어 문장으로 작성하세요.\n"
            f"- 등장인물의 성격과 세계관 규칙을 일관되게 유지하세요."
        )

        return "\n\n".join(sections)


    # ─── 12.2 챕터 생성 파이프라인 ───────────────────────────────────────────

    async def generate_chapter(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        chapter_number: int,
        parameters: GenerationParameters,
        user_id: uuid.UUID,
        user_prompt: Optional[str] = None,
    ):
        """
        전체 챕터 생성 파이프라인을 실행합니다.

        파이프라인 순서:
        1. ContextManager에서 StoryContext 조회
        2. RAG 시스템으로 관련 이전 구절 검색
        3. 프롬프트 구성 (_build_prompt)
        4. Qwen API 호출 (최소 2,000자 보장, 필요 시 재시도)
        5. ChapterManager로 챕터 저장
        6. GenerationLog 저장
        7. RAG에 새 챕터 임베딩
        8. StoryContext 캐시 갱신

        Args:
            db: 비동기 DB 세션
            project_id: 프로젝트 ID
            chapter_number: 생성할 챕터 번호
            parameters: 생성 파라미터
            user_id: 요청 사용자 ID
            user_prompt: 사용자 지정 프롬프트 (선택)

        Returns:
            생성된 Chapter ORM 객체

        Raises:
            NovelGeneratorError: 생성 파이프라인 실패 시
        """
        logger.info(
            "챕터 생성 시작: project_id=%s, chapter_number=%d",
            project_id, chapter_number,
        )

        try:
            # 1) StoryContext 조회
            story_context = await context_manager.get_story_context(db, project_id)
            logger.info(
                "StoryContext 조회 완료: project_id=%s, characters=%d, plot_points=%d",
                project_id,
                len(story_context.characters),
                len(story_context.plot_points),
            )

            # 2) RAG 검색 쿼리 구성
            rag_query = self._build_rag_query(parameters, story_context, user_prompt)
            relevant_passages = await rag_system.retrieve_relevant_passages(
                query=rag_query,
                project_id=str(project_id),
                top_k=5,
            )
            logger.info(
                "RAG 검색 완료: project_id=%s, passages=%d",
                project_id, len(relevant_passages),
            )

            # 3) 프롬프트 구성
            prompt = self._build_prompt(
                story_context=story_context,
                relevant_passages=relevant_passages,
                parameters=parameters,
                chapter_number=chapter_number,
                user_prompt=user_prompt or parameters.user_prompt,
            )

            # 4) Qwen API 호출
            ai_response = await self._generate_with_length_guarantee(
                prompt=prompt,
                parameters=parameters,
                db=db,
                user_id=user_id,
            )

            generated_text = ai_response.text

            # 5) 챕터 제목 추출
            title = self._extract_title(generated_text, chapter_number)

            # 6) ChapterManager로 챕터 저장
            chapter = await chapter_manager.create_chapter(
                db=db,
                project_id=project_id,
                data=ChapterCreate(
                    chapter_number=chapter_number,
                    title=title,
                    content=generated_text,
                    word_count=len(generated_text),
                ),
            )
            await db.commit()
            await db.refresh(chapter)

            logger.info(
                "챕터 저장 완료: chapter_id=%s, chapter_number=%d, length=%d",
                chapter.id, chapter_number, len(generated_text),
            )

            # 7) GenerationLog 저장
            await self._save_generation_log(
                db=db,
                chapter_id=chapter.id,
                user_id=user_id,
                ai_response=ai_response,
                parameters=parameters,
            )

            # 8) RAG 임베딩 (비동기 - 실패해도 챕터 저장은 유지)
            try:
                await rag_system.embed_chapter(
                    chapter_id=str(chapter.id),
                    content=generated_text,
                    project_id=str(project_id),
                    chapter_number=chapter_number,
                )
            except Exception as rag_exc:
                logger.warning(
                    "RAG 임베딩 실패 (챕터는 저장됨): chapter_id=%s, error=%s",
                    chapter.id, rag_exc,
                )

            # 9) StoryContext 캐시 갱신
            try:
                await context_manager.update_context(db, project_id)
            except Exception as ctx_exc:
                logger.warning(
                    "StoryContext 캐시 갱신 실패: project_id=%s, error=%s",
                    project_id, ctx_exc,
                )

            logger.info(
                "챕터 생성 파이프라인 완료: chapter_id=%s, project_id=%s",
                chapter.id, project_id,
            )
            return chapter

        except NovelGeneratorError:
            raise
        except Exception as exc:
            logger.error(
                "챕터 생성 파이프라인 실패: project_id=%s, error=%s",
                project_id, exc, exc_info=True,
            )
            raise NovelGeneratorError(
                f"챕터 생성 중 오류가 발생했습니다: {exc}"
            ) from exc


    # ─── 12.3 챕터 재생성 ────────────────────────────────────────────────────

    async def regenerate_chapter(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
        parameters: GenerationParameters,
        user_id: uuid.UUID,
        feedback: Optional[UserFeedback] = None,
    ):
        """
        기존 챕터를 사용자 피드백을 반영하여 재생성합니다.

        기존 StoryContext를 보존하면서 피드백(톤 조정, 플롯 방향, 추가 지시사항)을
        프롬프트에 반영하여 새 내용을 생성합니다.
        ChapterManager의 update_chapter를 통해 버전 히스토리를 유지합니다.

        Args:
            db: 비동기 DB 세션
            chapter_id: 재생성할 챕터 ID
            parameters: 생성 파라미터
            user_id: 요청 사용자 ID
            feedback: 사용자 피드백 (톤 조정, 플롯 방향, 추가 지시사항)

        Returns:
            재생성된 Chapter ORM 객체

        Raises:
            NovelGeneratorError: 재생성 파이프라인 실패 시
        """
        logger.info(
            "챕터 재생성 시작: chapter_id=%s",
            chapter_id,
        )

        try:
            # 기존 챕터 조회
            existing_chapter = await chapter_manager.get_chapter(db, chapter_id)
            project_id = existing_chapter.project_id
            chapter_number = existing_chapter.chapter_number

            logger.info(
                "기존 챕터 조회 완료: chapter_id=%s, chapter_number=%d, project_id=%s",
                chapter_id, chapter_number, project_id,
            )

            # 1) 기존 StoryContext 보존 (캐시 우선 조회)
            story_context = await context_manager.get_story_context(db, project_id)

            # 2) RAG 검색
            rag_query = self._build_rag_query(parameters, story_context, parameters.user_prompt)
            relevant_passages = await rag_system.retrieve_relevant_passages(
                query=rag_query,
                project_id=str(project_id),
                top_k=5,
            )

            # 3) 피드백 포함 프롬프트 구성
            prompt = self._build_prompt(
                story_context=story_context,
                relevant_passages=relevant_passages,
                parameters=parameters,
                chapter_number=chapter_number,
                user_prompt=parameters.user_prompt,
                feedback=feedback,
            )

            # 4) Qwen API 호출 (최소 길이 보장)
            ai_response = await self._generate_with_length_guarantee(
                prompt=prompt,
                parameters=parameters,
                db=db,
                user_id=user_id,
                chapter_id=chapter_id,
            )

            generated_text = ai_response.text

            # 5) 챕터 제목 추출
            title = self._extract_title(generated_text, chapter_number)

            # 6) ChapterManager로 챕터 업데이트 (버전 자동 저장)
            updated_chapter = await chapter_manager.update_chapter(
                db=db,
                chapter_id=chapter_id,
                data=ChapterUpdate(
                    title=title,
                    content=generated_text,
                    word_count=len(generated_text),
                ),
            )
            await db.commit()
            await db.refresh(updated_chapter)

            logger.info(
                "챕터 업데이트 완료: chapter_id=%s, length=%d",
                chapter_id, len(generated_text),
            )

            # 7) GenerationLog 저장
            await self._save_generation_log(
                db=db,
                chapter_id=chapter_id,
                user_id=user_id,
                ai_response=ai_response,
                parameters=parameters,
            )

            # 8) RAG 임베딩 업데이트
            try:
                await rag_system.update_embeddings(
                    chapter_id=str(chapter_id),
                    updated_content=generated_text,
                    project_id=str(project_id),
                    chapter_number=chapter_number,
                )
            except Exception as rag_exc:
                logger.warning(
                    "RAG 임베딩 업데이트 실패 (챕터는 저장됨): chapter_id=%s, error=%s",
                    chapter_id, rag_exc,
                )

            # 9) StoryContext 캐시 갱신
            try:
                await context_manager.update_context(db, project_id)
            except Exception as ctx_exc:
                logger.warning(
                    "StoryContext 캐시 갱신 실패: project_id=%s, error=%s",
                    project_id, ctx_exc,
                )

            logger.info(
                "챕터 재생성 파이프라인 완료: chapter_id=%s",
                chapter_id,
            )
            return updated_chapter

        except NovelGeneratorError:
            raise
        except Exception as exc:
            logger.error(
                "챕터 재생성 파이프라인 실패: chapter_id=%s, error=%s",
                chapter_id, exc, exc_info=True,
            )
            raise NovelGeneratorError(
                f"챕터 재생성 중 오류가 발생했습니다: {exc}"
            ) from exc


    # ─── 내부 헬퍼 메서드 ─────────────────────────────────────────────────────

    async def _generate_with_length_guarantee(
        self,
        prompt: str,
        parameters: GenerationParameters,
        db: AsyncSession,
        user_id: uuid.UUID,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> AIModelResponse:
        """
        최소 2,000자 한국어 생성을 보장하는 Qwen API 호출 래퍼.

        첫 번째 시도에서 길이가 부족하면 max_tokens를 최대값(8000)으로 늘리고
        명시적인 길이 지시사항을 추가하여 한 번 더 시도합니다.

        Args:
            prompt: 생성 프롬프트
            parameters: 생성 파라미터
            db: 비동기 DB 세션
            user_id: 요청 사용자 ID
            chapter_id: 관련 챕터 ID (선택)

        Returns:
            AIModelResponse

        Raises:
            NovelGeneratorError: API 호출 실패 시
        """
        from backend.app.services.qwen_client import QwenAPIError

        try:
            ai_response = await qwen_client.generate_text(
                prompt=prompt,
                parameters=parameters,
                db=db,
                user_id=user_id,
                chapter_id=chapter_id,
            )
        except QwenAPIError as exc:
            raise NovelGeneratorError(
                f"Qwen API 호출 실패: {exc}"
            ) from exc

        # 최소 길이 검증
        if len(ai_response.text) < MIN_CHAPTER_LENGTH:
            logger.warning(
                "생성된 텍스트가 최소 길이 미달 (%d자 < %d자), 재시도 중",
                len(ai_response.text), MIN_CHAPTER_LENGTH,
            )

            # 재시도: max_tokens 증가 + 명시적 길이 지시사항 추가
            retry_prompt = (
                prompt
                + f"\n\n[중요] 반드시 {MIN_CHAPTER_LENGTH}자 이상의 한국어 산문을 작성하세요. "
                f"현재 내용이 너무 짧습니다. 더 자세하고 풍부한 묘사와 대화를 포함하여 "
                f"최소 {MIN_CHAPTER_LENGTH}자 이상 작성해 주세요."
            )

            # max_tokens를 최대값으로 설정
            retry_parameters = parameters.model_copy(
                update={"max_tokens": MAX_TOKENS_RETRY}
            )

            try:
                ai_response = await qwen_client.generate_text(
                    prompt=retry_prompt,
                    parameters=retry_parameters,
                    db=db,
                    user_id=user_id,
                    chapter_id=chapter_id,
                )
                logger.info(
                    "재시도 후 생성 완료: length=%d자",
                    len(ai_response.text),
                )
            except QwenAPIError as exc:
                raise NovelGeneratorError(
                    f"Qwen API 재시도 호출 실패: {exc}"
                ) from exc

        return ai_response

    def _build_rag_query(
        self,
        parameters: GenerationParameters,
        story_context: StoryContext,
        user_prompt: Optional[str] = None,
    ) -> str:
        """
        RAG 검색에 사용할 쿼리 문자열을 구성합니다.

        사용자 프롬프트가 있으면 우선 사용하고,
        없으면 장르 + 톤 + 최근 챕터 요약을 조합합니다.

        Args:
            parameters: 생성 파라미터
            story_context: 현재 스토리 컨텍스트
            user_prompt: 사용자 지정 프롬프트 (선택)

        Returns:
            RAG 검색 쿼리 문자열
        """
        if user_prompt:
            return user_prompt

        genre_ko = GENRE_KO_MAP.get(parameters.genre, parameters.genre.value)
        tone_ko = TONE_KO_MAP.get(parameters.tone, parameters.tone.value)

        query_parts = [f"{genre_ko} 소설", f"{tone_ko} 문체"]

        # 현재 플롯 포인트 추가
        for pp in story_context.plot_points:
            if not pp.is_completed:
                query_parts.append(pp.title)
                if pp.description:
                    query_parts.append(pp.description[:100])
                break

        # 최근 챕터 요약 일부 추가
        if story_context.recent_chapters_summary:
            query_parts.append(story_context.recent_chapters_summary[:200])

        return " ".join(query_parts)

    @staticmethod
    def _extract_title(content: str, chapter_number: int) -> str:
        """
        생성된 챕터 내용에서 제목을 추출합니다.

        첫 번째 줄이 50자 미만이고 제목처럼 보이면 제목으로 사용합니다.
        그렇지 않으면 기본 형식 "챕터 {chapter_number}"를 반환합니다.

        Args:
            content: 생성된 챕터 내용
            chapter_number: 챕터 번호

        Returns:
            챕터 제목 문자열
        """
        lines = content.strip().split("\n")
        if lines:
            first_line = lines[0].strip()
            # 첫 줄이 50자 미만이고 비어있지 않으면 제목으로 간주
            if first_line and len(first_line) < 50:
                return first_line
        return f"챕터 {chapter_number}"

    async def _save_generation_log(
        self,
        db: AsyncSession,
        chapter_id: uuid.UUID,
        user_id: uuid.UUID,
        ai_response: AIModelResponse,
        parameters: GenerationParameters,
    ) -> None:
        """
        생성 로그를 DB에 저장합니다.

        Args:
            db: 비동기 DB 세션
            chapter_id: 챕터 ID
            user_id: 사용자 ID
            ai_response: AI 모델 응답
            parameters: 생성 파라미터
        """
        try:
            log_entry = GenerationLog(
                id=uuid.uuid4(),
                chapter_id=chapter_id,
                user_id=user_id,
                response_time_ms=ai_response.response_time_ms,
                token_count=ai_response.total_tokens,
                consistency_score=None,
                parameters={
                    "genre": parameters.genre.value,
                    "tone": parameters.tone.value,
                    "temperature": parameters.temperature,
                    "top_p": parameters.top_p,
                    "max_tokens": parameters.max_tokens,
                    "model": ai_response.model,
                    "finish_reason": ai_response.finish_reason,
                },
                error_message=None,
            )
            db.add(log_entry)
            await db.flush()
            logger.info(
                "GenerationLog 저장 완료: log_id=%s, chapter_id=%s",
                log_entry.id, chapter_id,
            )
        except Exception as exc:
            # 로그 저장 실패는 챕터 생성을 막지 않음
            logger.warning(
                "GenerationLog 저장 실패: chapter_id=%s, error=%s",
                chapter_id, exc,
            )


# ─── 싱글턴 인스턴스 (의존성 주입용) ─────────────────────────────────────────

novel_generator = NovelGeneratorService()
