"""
보안 유틸리티 모듈
- bcrypt 기반 비밀번호 해싱/검증
- JWT 액세스/리프레시 토큰 생성 및 검증
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from backend.app.config import settings

# 토큰 타입 상수
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ─── 비밀번호 유틸리티 ────────────────────────────────────────────────────────


def hash_password(plain_password: str) -> str:
    """
    평문 비밀번호를 bcrypt 해시로 변환합니다.
    
    bcrypt는 최대 72바이트까지만 처리하므로, 긴 비밀번호는 자동으로 잘립니다.
    """
    # bcrypt는 72바이트 제한이 있으므로 UTF-8 인코딩 후 잘라냄
    password_bytes = plain_password.encode('utf-8')[:72]
    
    # bcrypt로 해싱
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # 문자열로 반환 (데이터베이스 저장용)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    평문 비밀번호와 bcrypt 해시를 비교합니다.
    
    bcrypt는 최대 72바이트까지만 처리하므로, 긴 비밀번호는 자동으로 잘립니다.
    """
    # bcrypt는 72바이트 제한이 있으므로 UTF-8 인코딩 후 잘라냄
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    
    # bcrypt로 검증
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ─── JWT 토큰 유틸리티 ────────────────────────────────────────────────────────


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    JWT 토큰을 생성하는 내부 헬퍼 함수.

    Args:
        subject: 토큰 주체 (일반적으로 user_id 문자열)
        token_type: 토큰 유형 ("access" 또는 "refresh")
        expires_delta: 만료 시간 델타
        extra_claims: 추가 페이로드 클레임 (선택)

    Returns:
        서명된 JWT 문자열
    """
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: UUID | str) -> str:
    """
    액세스 토큰을 생성합니다 (만료: 30분).

    Args:
        user_id: 사용자 UUID

    Returns:
        서명된 JWT 액세스 토큰
    """
    return _create_token(
        subject=str(user_id),
        token_type=TOKEN_TYPE_ACCESS,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: UUID | str) -> str:
    """
    리프레시 토큰을 생성합니다 (만료: 7일).

    Args:
        user_id: 사용자 UUID

    Returns:
        서명된 JWT 리프레시 토큰
    """
    return _create_token(
        subject=str(user_id),
        token_type=TOKEN_TYPE_REFRESH,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """
    JWT 토큰을 디코딩하고 페이로드를 반환합니다.

    Args:
        token: JWT 문자열

    Returns:
        디코딩된 페이로드 딕셔너리

    Raises:
        JWTError: 토큰이 유효하지 않거나 만료된 경우
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def decode_access_token(token: str) -> str:
    """
    액세스 토큰을 검증하고 user_id(sub)를 반환합니다.

    Args:
        token: JWT 액세스 토큰 문자열

    Returns:
        user_id 문자열

    Raises:
        JWTError: 토큰이 유효하지 않거나 타입이 다른 경우
    """
    payload = decode_token(token)
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise JWTError("액세스 토큰이 아닙니다.")
    sub: Optional[str] = payload.get("sub")
    if sub is None:
        raise JWTError("토큰에 subject(sub) 클레임이 없습니다.")
    return sub


def decode_refresh_token(token: str) -> str:
    """
    리프레시 토큰을 검증하고 user_id(sub)를 반환합니다.

    Args:
        token: JWT 리프레시 토큰 문자열

    Returns:
        user_id 문자열

    Raises:
        JWTError: 토큰이 유효하지 않거나 타입이 다른 경우
    """
    payload = decode_token(token)
    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise JWTError("리프레시 토큰이 아닙니다.")
    sub: Optional[str] = payload.get("sub")
    if sub is None:
        raise JWTError("토큰에 subject(sub) 클레임이 없습니다.")
    return sub
