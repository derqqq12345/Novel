"""
인증 관련 Pydantic 스키마 (DTO)
"""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """회원가입 요청 스키마"""

    email: EmailStr
    password: str = Field(min_length=8, description="최소 8자 이상의 비밀번호")
    username: str = Field(min_length=2, max_length=100, description="사용자 이름")


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """토큰 응답 스키마"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """토큰 갱신 요청 스키마"""

    refresh_token: str


class MessageResponse(BaseModel):
    """단순 메시지 응답 스키마"""

    message: str
