"""
FastAPI 공통 의존성 모듈
- get_current_user: JWT 검증 후 현재 사용자 반환
- RateLimiter: Redis 기반 슬라이딩 윈도우 속도 제한
"""
import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.core.security import decode_access_token
from backend.app.database import get_db
from backend.app.models.user import User

# Bearer 토큰 추출기 (auto_error=False → 직접 에러 처리)
_bearer_scheme = HTTPBearer(auto_error=False)

# ─── Redis 클라이언트 (싱글턴) ────────────────────────────────────────────────

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Redis 클라이언트 싱글턴을 반환합니다."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


# ─── JWT 인증 의존성 ──────────────────────────────────────────────────────────


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Authorization: Bearer <token> 헤더에서 JWT를 추출하고 검증한 뒤
    해당 사용자 ORM 객체를 반환합니다.

    Raises:
        HTTPException 401: 토큰 없음, 유효하지 않음, 만료됨
        HTTPException 403: 비활성화된 계정
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_str = decode_access_token(credentials.credentials)
        user_uuid = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_uuid))
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )

    return user


# 타입 별칭 — 라우터에서 편리하게 사용
CurrentUser = Annotated[User, Depends(get_current_user)]


# ─── Redis 기반 속도 제한 미들웨어 ────────────────────────────────────────────


class RateLimiter:
    """
    Redis 슬라이딩 윈도우 방식의 속도 제한기.

    사용 예시 (라우터 의존성):
        @router.get("/items", dependencies=[Depends(RateLimiter())])

    또는 미들웨어로 전역 적용:
        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(
        self,
        requests_per_minute: int = settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60

    async def __call__(
        self,
        request: Request,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
        ] = None,
    ) -> None:
        """
        요청 당 속도 제한을 적용합니다.
        인증된 사용자는 user_id 기반, 미인증 요청은 IP 기반으로 키를 구성합니다.
        """
        # 식별자 결정: 인증 토큰 > 클라이언트 IP
        identifier: str
        if credentials is not None:
            try:
                user_id_str = decode_access_token(credentials.credentials)
                identifier = f"user:{user_id_str}"
            except (JWTError, ValueError):
                identifier = f"ip:{request.client.host if request.client else 'unknown'}"
        else:
            identifier = f"ip:{request.client.host if request.client else 'unknown'}"

        redis = get_redis()
        key = f"rate_limit:{identifier}"

        try:
            # INCR + EXPIRE 원자적 처리 (Lua 스크립트)
            lua_script = """
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then
                redis.call('EXPIRE', KEYS[1], ARGV[1])
            end
            return current
            """
            current_count = await redis.eval(
                lua_script, 1, key, str(self.window_seconds)
            )

            if current_count > self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"속도 제한 초과: 분당 최대 {self.requests_per_minute}회 요청 가능합니다.",
                    headers={"Retry-After": str(self.window_seconds)},
                )
        except HTTPException:
            raise
        except Exception:
            # Redis 연결 실패 시 속도 제한을 건너뜁니다 (fail-open 정책)
            pass
