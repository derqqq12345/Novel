"""
Celery 태스크: 소설 챕터 생성 비동기 작업

챕터 생성 파이프라인을 Celery 워커에서 비동기로 실행합니다.
asyncio.run()을 사용하여 비동기 서비스를 동기 Celery 태스크에서 호출합니다.
"""
import asyncio
import logging
import uuid
from typing import Any, Dict, Optional

from backend.app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="novel_tasks.generate_chapter_task",
    max_retries=2,
    default_retry_delay=30,
)
def generate_chapter_task(
    self,
    project_id: str,
    chapter_number: int,
    parameters_dict: Dict[str, Any],
    user_id: str,
    user_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    챕터 생성 Celery 태스크.

    NovelGeneratorService.generate_chapter()를 비동기로 실행하고
    생성된 챕터 정보를 딕셔너리로 반환합니다.

    Args:
        project_id: 프로젝트 ID (문자열)
        chapter_number: 생성할 챕터 번호
        parameters_dict: GenerationParameters 딕셔너리
        user_id: 요청 사용자 ID (문자열)
        user_prompt: 사용자 지정 프롬프트 (선택)

    Returns:
        생성된 챕터 정보 딕셔너리:
        {
            "chapter_id": str,
            "chapter_number": int,
            "title": str,
            "word_count": int,
            "status": "completed"
        }

    Raises:
        celery.exceptions.Retry: 재시도 가능한 오류 발생 시
    """
    logger.info(
        "챕터 생성 태스크 시작: project_id=%s, chapter_number=%d",
        project_id, chapter_number,
    )

    async def _run() -> Dict[str, Any]:
        from backend.app.database import AsyncSessionLocal
        from backend.app.schemas.generation import GenerationParameters
        from backend.app.services.novel_generator import novel_generator

        parameters = GenerationParameters(**parameters_dict)
        project_uuid = uuid.UUID(project_id)
        user_uuid = uuid.UUID(user_id)

        async with AsyncSessionLocal() as db:
            chapter = await novel_generator.generate_chapter(
                db=db,
                project_id=project_uuid,
                chapter_number=chapter_number,
                parameters=parameters,
                user_id=user_uuid,
                user_prompt=user_prompt,
            )
            return {
                "chapter_id": str(chapter.id),
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "word_count": chapter.word_count,
                "status": "completed",
            }

    try:
        result = asyncio.run(_run())
        logger.info(
            "챕터 생성 태스크 완료: project_id=%s, chapter_id=%s",
            project_id, result.get("chapter_id"),
        )
        return result

    except Exception as exc:
        logger.error(
            "챕터 생성 태스크 실패: project_id=%s, error=%s",
            project_id, exc, exc_info=True,
        )
        # 재시도 가능한 오류인 경우 Celery 재시도
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "챕터 생성 태스크 최대 재시도 초과: project_id=%s",
                project_id,
            )
            raise


@celery_app.task(
    bind=True,
    name="novel_tasks.regenerate_chapter_task",
    max_retries=2,
    default_retry_delay=30,
)
def regenerate_chapter_task(
    self,
    chapter_id: str,
    parameters_dict: Dict[str, Any],
    user_id: str,
    feedback_dict: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    챕터 재생성 Celery 태스크.

    NovelGeneratorService.regenerate_chapter()를 비동기로 실행하고
    재생성된 챕터 정보를 딕셔너리로 반환합니다.

    Args:
        chapter_id: 재생성할 챕터 ID (문자열)
        parameters_dict: GenerationParameters 딕셔너리
        user_id: 요청 사용자 ID (문자열)
        feedback_dict: UserFeedback 딕셔너리 (선택)

    Returns:
        재생성된 챕터 정보 딕셔너리:
        {
            "chapter_id": str,
            "chapter_number": int,
            "title": str,
            "word_count": int,
            "status": "regenerated"
        }
    """
    logger.info(
        "챕터 재생성 태스크 시작: chapter_id=%s",
        chapter_id,
    )

    async def _run() -> Dict[str, Any]:
        from backend.app.database import AsyncSessionLocal
        from backend.app.schemas.generation import GenerationParameters, UserFeedback
        from backend.app.services.novel_generator import novel_generator

        parameters = GenerationParameters(**parameters_dict)
        chapter_uuid = uuid.UUID(chapter_id)
        user_uuid = uuid.UUID(user_id)
        feedback = UserFeedback(**feedback_dict) if feedback_dict else None

        async with AsyncSessionLocal() as db:
            chapter = await novel_generator.regenerate_chapter(
                db=db,
                chapter_id=chapter_uuid,
                parameters=parameters,
                user_id=user_uuid,
                feedback=feedback,
            )
            return {
                "chapter_id": str(chapter.id),
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "word_count": chapter.word_count,
                "status": "regenerated",
            }

    try:
        result = asyncio.run(_run())
        logger.info(
            "챕터 재생성 태스크 완료: chapter_id=%s",
            chapter_id,
        )
        return result

    except Exception as exc:
        logger.error(
            "챕터 재생성 태스크 실패: chapter_id=%s, error=%s",
            chapter_id, exc, exc_info=True,
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error(
                "챕터 재생성 태스크 최대 재시도 초과: chapter_id=%s",
                chapter_id,
            )
            raise
