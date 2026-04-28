"""
사용자 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}
