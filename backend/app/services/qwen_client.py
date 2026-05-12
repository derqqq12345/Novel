"""
Qwen API 클라이언트 모듈

Qwen AI 모델(DashScope OpenAI 호환 API)을 호출하여 텍스트를 생성합니다.
AIModelAdapter 인터페이스를 구현하여 플러그인 방식으로 교체 가능합니다.

주요 기능:
- 비동기 HTTP 클라이언트 (httpx)
- 지수 백오프 재시도 로직 (3회, 1s/2s/4s)
- 스트리밍 응답 지원 (SSE)
- 실패한 요청 DB 저장
- 구조화된 로깅
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Callable, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models.generation_log import GenerationLog
from backend.app.schemas.generation import GenerationParameters

logger = logging.getLogger(__name__)

# Qwen API 기본 설정
QWEN_API_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_DEFAULT_MODEL = "qwen-max"
QWEN_MAX_CONTEXT_TOKENS = 128_000
QWEN_REQUEST_TIMEOUT = 120.0  # 초

# 재시도 설정
RETRY_DELAYS = [1.0, 2.0, 4.0]  # 지수 백오프 (초)
MAX_RETRIES = 3

# 스트리밍 진행률 업데이트 임계값 (초)
STREAMING_PROGRESS_THRESHOLD = 5.0


# ─── 예외 클래스 ──────────────────────────────────────────────────────────────


class QwenAPIError(Exception):
    """Qwen API 호출 실패 시 발생하는 기본 예외"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class QwenAuthenticationError(QwenAPIError):
    """API 키가 유효하지 않거나 만료된 경우"""
    pass


class QwenRateLimitError(QwenAPIError):
    """API 속도 제한 초과 시 발생하는 예외"""
    pass


class QwenTimeoutError(QwenAPIError):
    """요청 타임아웃 (30초 초과) 시 발생하는 예외"""
    pass


class QwenInvalidResponseError(QwenAPIError):
    """API 응답 형식이 올바르지 않은 경우"""
    pass


# ─── 데이터 모델 ──────────────────────────────────────────────────────────────


class QwenParameters:
    """Qwen API 호출 파라미터"""

    def __init__(
        self,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 3000,
        model: str = QWEN_DEFAULT_MODEL,
    ) -> None:
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.model = model

    @classmethod
    def from_generation_parameters(cls, params: GenerationParameters, model: str = QWEN_DEFAULT_MODEL) -> "QwenParameters":
        """GenerationParameters 스키마에서 QwenParameters를 생성합니다."""
        return cls(
            temperature=params.temperature,
            top_p=params.top_p,
            max_tokens=params.max_tokens,
            model=model,
        )


class QwenResponse:
    """Qwen API 응답 데이터"""

    def __init__(
        self,
        text: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        finish_reason: str,
        response_time_ms: int,
    ) -> None:
        self.text = text
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.finish_reason = finish_reason
        self.response_time_ms = response_time_ms


class AIModelResponse:
    """AI 모델 어댑터 공통 응답 형식"""

    def __init__(
        self,
        text: str,
        model: str,
        total_tokens: int,
        response_time_ms: int,
        finish_reason: str = "stop",
    ) -> None:
        self.text = text
        self.model = model
        self.total_tokens = total_tokens
        self.response_time_ms = response_time_ms
        self.finish_reason = finish_reason


# ─── AI 모델 어댑터 추상 인터페이스 ──────────────────────────────────────────


class AIModelAdapter(ABC):
    """
    모든 AI 모델 클라이언트가 구현해야 하는 추상 인터페이스.

    Strategy 패턴 적용 - 모델별 구현체를 런타임에 교체 가능.
    """

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        parameters: GenerationParameters,
    ) -> AIModelResponse:
        """텍스트 생성 - 모든 모델 공통 인터페이스"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        parameters: GenerationParameters,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 텍스트 생성"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """모델 식별자"""
        pass

    @property
    @abstractmethod
    def max_context_tokens(self) -> int:
        """최대 컨텍스트 토큰 수"""
        pass


# ─── Qwen API 클라이언트 ──────────────────────────────────────────────────────


class QwenAPIClient(AIModelAdapter):
    """
    Qwen AI 모델 API 클라이언트.

    DashScope OpenAI 호환 API를 사용하여 텍스트를 생성합니다.
    AIModelAdapter 인터페이스를 구현하여 플러그인 방식으로 교체 가능합니다.

    사용 예시:
        client = QwenAPIClient()
        response = await client.generate_text(prompt, parameters)

        # 스트리밍
        async for chunk in client.generate_stream(prompt, parameters):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = QWEN_API_BASE_URL,
        model: str = QWEN_DEFAULT_MODEL,
        timeout: float = QWEN_REQUEST_TIMEOUT,
    ) -> None:
        self._api_key = api_key or getattr(settings, "QWEN_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def max_context_tokens(self) -> int:
        return QWEN_MAX_CONTEXT_TOKENS

    def _build_headers(self) -> dict[str, str]:
        """API 요청 헤더를 구성합니다."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_request_body(
        self,
        prompt: str,
        parameters: QwenParameters,
        stream: bool = False,
    ) -> dict[str, Any]:
        """API 요청 본문을 구성합니다."""
        return {
            "model": parameters.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": parameters.temperature,
            "top_p": parameters.top_p,
            "max_tokens": parameters.max_tokens,
            "stream": stream,
        }

    def _parse_error_response(self, status_code: int, response_body: str) -> QwenAPIError:
        """HTTP 에러 응답을 적절한 예외로 변환합니다."""
        if status_code == 401:
            return QwenAuthenticationError(
                "Qwen API 인증 실패: API 키가 유효하지 않거나 만료되었습니다.",
                status_code=status_code,
                response_body=response_body,
            )
        if status_code == 429:
            return QwenRateLimitError(
                "Qwen API 속도 제한 초과: 잠시 후 다시 시도하세요.",
                status_code=status_code,
                response_body=response_body,
            )
        return QwenAPIError(
            f"Qwen API 호출 실패 (HTTP {status_code})",
            status_code=status_code,
            response_body=response_body,
        )

    async def _retry_with_backoff(
        self,
        request_func: Callable[[], Any],
        max_retries: int = MAX_RETRIES,
    ) -> Any:
        """
        지수 백오프를 사용한 재시도 로직.

        Args:
            request_func: 재시도할 비동기 함수 (인자 없는 callable)
            max_retries: 최대 재시도 횟수 (기본값: 3)

        Returns:
            request_func의 반환값

        Raises:
            QwenAPIError: 모든 재시도 실패 후 마지막 예외
            QwenAuthenticationError: 인증 오류 (재시도 없음)
        """
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                return await request_func()
            except QwenAuthenticationError:
                # 인증 오류는 재시도해도 의미 없음
                raise
            except (QwenRateLimitError, QwenTimeoutError, QwenAPIError) as exc:
                last_exception = exc
                if attempt < max_retries:
                    delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                    logger.warning(
                        "Qwen API 요청 실패, 재시도 중",
                        extra={
                            "attempt": attempt + 1,
                            "max_retries": max_retries,
                            "delay_seconds": delay,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Qwen API 요청 최종 실패",
                        extra={
                            "attempts": max_retries + 1,
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )

        raise last_exception  # type: ignore[misc]

    async def _save_failed_request_to_db(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        prompt: str,
        parameters: QwenParameters,
        error_message: str,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> None:
        """
        실패한 요청을 generation_logs 테이블에 저장합니다.

        나중에 재시도할 수 있도록 요청 파라미터와 에러 메시지를 보존합니다.

        Args:
            db: 비동기 DB 세션
            user_id: 요청한 사용자 ID
            prompt: 생성 프롬프트 (처음 500자만 저장)
            parameters: Qwen API 파라미터
            error_message: 에러 메시지
            chapter_id: 관련 챕터 ID (선택)
        """
        try:
            log_entry = GenerationLog(
                id=uuid.uuid4(),
                chapter_id=chapter_id,
                user_id=user_id,
                response_time_ms=None,
                token_count=None,
                consistency_score=None,
                parameters={
                    "model": parameters.model,
                    "temperature": parameters.temperature,
                    "top_p": parameters.top_p,
                    "max_tokens": parameters.max_tokens,
                    "prompt_preview": prompt[:500],  # 처음 500자만 저장
                },
                error_message=error_message,
            )
            db.add(log_entry)
            await db.flush()
            logger.info(
                "실패한 Qwen API 요청을 DB에 저장했습니다",
                extra={"log_id": str(log_entry.id), "user_id": str(user_id)},
            )
        except Exception as db_exc:
            # DB 저장 실패는 원래 에러를 가리지 않도록 로그만 남김
            logger.error(
                "실패한 요청 DB 저장 중 오류 발생",
                extra={"error": str(db_exc)},
            )

    async def generate_text(
        self,
        prompt: str,
        parameters: GenerationParameters,
        db: Optional[AsyncSession] = None,
        user_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> AIModelResponse:
        """
        Qwen 모델을 호출하여 텍스트를 생성합니다 (AIModelAdapter 인터페이스 구현).

        Args:
            prompt: 생성 프롬프트
            parameters: GenerationParameters (장르, 톤, temperature 등)
            db: 비동기 DB 세션 (실패 로깅용, 선택)
            user_id: 요청 사용자 ID (실패 로깅용, 선택)
            chapter_id: 관련 챕터 ID (실패 로깅용, 선택)

        Returns:
            AIModelResponse: 생성된 텍스트 및 메타데이터

        Raises:
            QwenAPIError: API 호출 실패
            QwenRateLimitError: 속도 제한 초과
            QwenTimeoutError: 요청 타임아웃
        """
        qwen_params = QwenParameters.from_generation_parameters(parameters, model=self._model)
        qwen_response = await self._generate_text_raw(prompt, qwen_params, db=db, user_id=user_id, chapter_id=chapter_id)
        return AIModelResponse(
            text=qwen_response.text,
            model=qwen_response.model,
            total_tokens=qwen_response.total_tokens,
            response_time_ms=qwen_response.response_time_ms,
            finish_reason=qwen_response.finish_reason,
        )

    async def _generate_text_raw(
        self,
        prompt: str,
        parameters: QwenParameters,
        db: Optional[AsyncSession] = None,
        user_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> QwenResponse:
        """
        Qwen API를 직접 호출하여 QwenResponse를 반환합니다.

        Args:
            prompt: 생성 프롬프트
            parameters: QwenParameters
            db: 비동기 DB 세션 (실패 로깅용, 선택)
            user_id: 요청 사용자 ID (실패 로깅용, 선택)
            chapter_id: 관련 챕터 ID (실패 로깅용, 선택)

        Returns:
            QwenResponse

        Raises:
            QwenAPIError: API 호출 실패
        """
        request_body = self._build_request_body(prompt, parameters, stream=False)
        start_time = time.monotonic()

        logger.info(
            "Qwen API 텍스트 생성 요청",
            extra={
                "model": parameters.model,
                "temperature": parameters.temperature,
                "top_p": parameters.top_p,
                "max_tokens": parameters.max_tokens,
                "prompt_length": len(prompt),
            },
        )

        async def _do_request() -> QwenResponse:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                try:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=self._build_headers(),
                        json=request_body,
                    )
                except httpx.TimeoutException as exc:
                    raise QwenTimeoutError(
                        f"Qwen API 요청 타임아웃 ({self._timeout}초 초과)"
                    ) from exc
                except httpx.RequestError as exc:
                    raise QwenAPIError(f"Qwen API 네트워크 오류: {exc}") from exc

                if response.status_code != 200:
                    raise self._parse_error_response(response.status_code, response.text)

                try:
                    data = response.json()
                except Exception as exc:
                    raise QwenInvalidResponseError(
                        f"Qwen API 응답 파싱 실패: {exc}",
                        response_body=response.text,
                    ) from exc

                elapsed_ms = int((time.monotonic() - start_time) * 1000)

                try:
                    choice = data["choices"][0]
                    usage = data.get("usage", {})
                    generated_text = choice["message"]["content"]
                    finish_reason = choice.get("finish_reason", "stop")
                except (KeyError, IndexError) as exc:
                    raise QwenInvalidResponseError(
                        f"Qwen API 응답 구조가 올바르지 않습니다: {exc}",
                        response_body=response.text,
                    ) from exc

                logger.info(
                    "Qwen API 텍스트 생성 완료",
                    extra={
                        "model": data.get("model", parameters.model),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "finish_reason": finish_reason,
                        "response_time_ms": elapsed_ms,
                        "generated_length": len(generated_text),
                    },
                )

                return QwenResponse(
                    text=generated_text,
                    model=data.get("model", parameters.model),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    finish_reason=finish_reason,
                    response_time_ms=elapsed_ms,
                )

        try:
            return await self._retry_with_backoff(_do_request)
        except QwenAPIError as exc:
            # 실패한 요청을 DB에 저장 (db와 user_id가 제공된 경우)
            if db is not None and user_id is not None:
                await self._save_failed_request_to_db(
                    db=db,
                    user_id=user_id,
                    prompt=prompt,
                    parameters=parameters,
                    error_message=str(exc),
                    chapter_id=chapter_id,
                )
            raise

    async def generate_stream(
        self,
        prompt: str,
        parameters: GenerationParameters,
        db: Optional[AsyncSession] = None,
        user_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Qwen 모델을 호출하여 스트리밍 방식으로 텍스트를 생성합니다 (AIModelAdapter 인터페이스 구현).

        Server-Sent Events(SSE) 형식으로 청크를 수신하여 텍스트 조각을 yield합니다.
        생성이 5초 이상 소요되면 진행률 업데이트 메시지를 yield합니다.

        Args:
            prompt: 생성 프롬프트
            parameters: GenerationParameters
            db: 비동기 DB 세션 (실패 로깅용, 선택)
            user_id: 요청 사용자 ID (실패 로깅용, 선택)
            chapter_id: 관련 챕터 ID (실패 로깅용, 선택)

        Yields:
            str: 생성된 텍스트 청크

        Raises:
            QwenAPIError: API 호출 실패
            QwenRateLimitError: 속도 제한 초과
            QwenTimeoutError: 요청 타임아웃
        """
        qwen_params = QwenParameters.from_generation_parameters(parameters, model=self._model)
        async for chunk in self._generate_stream_raw(
            prompt, qwen_params, db=db, user_id=user_id, chapter_id=chapter_id
        ):
            yield chunk

    async def _generate_stream_raw(
        self,
        prompt: str,
        parameters: QwenParameters,
        db: Optional[AsyncSession] = None,
        user_id: Optional[uuid.UUID] = None,
        chapter_id: Optional[uuid.UUID] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Qwen API 스트리밍 호출 내부 구현.

        SSE 청크를 파싱하여 텍스트 조각을 yield합니다.
        5초 이상 소요 시 진행률 업데이트 메시지를 yield합니다.
        """
        request_body = self._build_request_body(prompt, parameters, stream=True)
        start_time = time.monotonic()
        progress_notified = False

        logger.info(
            "Qwen API 스트리밍 텍스트 생성 요청",
            extra={
                "model": parameters.model,
                "temperature": parameters.temperature,
                "max_tokens": parameters.max_tokens,
                "prompt_length": len(prompt),
            },
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                try:
                    async with client.stream(
                        "POST",
                        f"{self._base_url}/chat/completions",
                        headers=self._build_headers(),
                        json=request_body,
                    ) as response:
                        if response.status_code != 200:
                            body = await response.aread()
                            raise self._parse_error_response(response.status_code, body.decode())

                        total_tokens = 0
                        finish_reason = "stop"

                        async for line in response.aiter_lines():
                            # 5초 이상 소요 시 진행률 업데이트
                            elapsed = time.monotonic() - start_time
                            if elapsed > STREAMING_PROGRESS_THRESHOLD and not progress_notified:
                                progress_notified = True
                                logger.info(
                                    "Qwen API 스트리밍 진행 중",
                                    extra={"elapsed_seconds": round(elapsed, 1)},
                                )
                                # 진행률 업데이트를 특수 마커로 yield
                                yield f"[PROGRESS:{round(elapsed, 1)}s]"

                            # SSE 형식: "data: {...}" 또는 "data: [DONE]"
                            if not line.startswith("data: "):
                                continue

                            data_str = line[len("data: "):]

                            if data_str.strip() == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                logger.warning(
                                    "SSE 청크 파싱 실패",
                                    extra={"raw_line": line[:200]},
                                )
                                continue

                            # 토큰 사용량 추적 (마지막 청크에 포함될 수 있음)
                            usage = data.get("usage")
                            if usage:
                                total_tokens = usage.get("total_tokens", total_tokens)

                            choices = data.get("choices", [])
                            if not choices:
                                continue

                            choice = choices[0]
                            delta = choice.get("delta", {})
                            finish_reason = choice.get("finish_reason") or finish_reason
                            content = delta.get("content")

                            if content:
                                yield content

                        elapsed_ms = int((time.monotonic() - start_time) * 1000)
                        logger.info(
                            "Qwen API 스트리밍 텍스트 생성 완료",
                            extra={
                                "model": parameters.model,
                                "total_tokens": total_tokens,
                                "finish_reason": finish_reason,
                                "response_time_ms": elapsed_ms,
                            },
                        )

                except httpx.TimeoutException as exc:
                    raise QwenTimeoutError(
                        f"Qwen API 스트리밍 요청 타임아웃 ({self._timeout}초 초과)"
                    ) from exc
                except httpx.RequestError as exc:
                    raise QwenAPIError(f"Qwen API 네트워크 오류: {exc}") from exc

        except QwenAPIError as exc:
            # 실패한 요청을 DB에 저장 (db와 user_id가 제공된 경우)
            if db is not None and user_id is not None:
                await self._save_failed_request_to_db(
                    db=db,
                    user_id=user_id,
                    prompt=prompt,
                    parameters=parameters,
                    error_message=str(exc),
                    chapter_id=chapter_id,
                )
            raise


# ─── 싱글턴 인스턴스 (의존성 주입용) ─────────────────────────────────────────

qwen_client = QwenAPIClient()
