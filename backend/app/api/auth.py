"""
사용자 인증 API 엔드포인트
- POST /api/auth/register  회원가입
- POST /api/auth/login     로그인 (JWT 반환)
- POST /api/auth/refresh   액세스 토큰 갱신
- POST /api/auth/logout    로그아웃
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_user
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["인증"])


# ─── 회원가입 ─────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    새 사용자를 등록합니다.

    - 이메일 중복 검사
    - bcrypt 비밀번호 해싱
    - 사용자 DB 저장
    """
    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 이메일입니다.",
        )

    # 사용자 생성
    user = User(
        id=uuid.uuid4(),
        email=body.email,
        password_hash=hash_password(body.password),
        username=body.username,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # id 확보 (commit은 get_db에서 처리)

    return UserResponse.model_validate(user)


# ─── 로그인 ───────────────────────────────────────────────────────────────────


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="로그인",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    이메일/비밀번호로 로그인하고 JWT 토큰 쌍을 반환합니다.

    - 이메일로 사용자 조회
    - 비밀번호 검증
    - 액세스 토큰(30분) + 리프레시 토큰(7일) 발급
    - last_login 업데이트
    """
    # 사용자 조회
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    # 사용자 없음 또는 비밀번호 불일치 — 동일한 에러로 응답 (타이밍 공격 방지)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다. 관리자에게 문의하세요.",
        )

    # last_login 업데이트
    user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ─── 토큰 갱신 ────────────────────────────────────────────────────────────────


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="액세스 토큰 갱신",
)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    유효한 리프레시 토큰으로 새 액세스 토큰과 리프레시 토큰을 발급합니다.

    - 리프레시 토큰 검증
    - 사용자 활성 상태 확인
    - 새 토큰 쌍 반환 (토큰 로테이션)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않거나 만료된 리프레시 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id_str = decode_refresh_token(body.refresh_token)
    except JWTError:
        raise credentials_exception

    # 사용자 존재 및 활성 상태 확인
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_uuid))
    user: User | None = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    # 새 토큰 쌍 발급 (리프레시 토큰 로테이션)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ─── 로그아웃 ─────────────────────────────────────────────────────────────────


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="로그아웃",
)
async def logout() -> MessageResponse:
    """
    로그아웃 처리.

    JWT는 stateless이므로 서버 측에서 토큰을 무효화하지 않습니다.
    클라이언트는 저장된 토큰을 삭제해야 합니다.
    향후 Redis 블랙리스트를 통한 토큰 무효화로 확장 가능합니다.
    """
    return MessageResponse(message="로그아웃되었습니다. 클라이언트의 토큰을 삭제하세요.")


# ─── 현재 사용자 정보 조회 ────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 사용자 정보 조회",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    현재 로그인한 사용자의 정보를 반환합니다.

    - JWT 토큰에서 사용자 식별
    - 사용자 정보 반환 (비밀번호 제외)
    """
    return UserResponse.model_validate(current_user)
