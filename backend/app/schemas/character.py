"""
캐릭터 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="캐릭터 이름")
    age: Optional[int] = Field(None, ge=0, le=1000, description="캐릭터 나이")
    personality_traits: List[str] = Field(default_factory=list, description="성격 특성 목록")
    appearance: Optional[str] = Field(None, description="외모 설명")
    background: Optional[str] = Field(None, description="배경 설명")
    relationships: Dict[str, str] = Field(default_factory=dict, description="다른 캐릭터와의 관계")


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="캐릭터 이름")
    age: Optional[int] = Field(None, ge=0, le=1000, description="캐릭터 나이")
    personality_traits: Optional[List[str]] = Field(None, description="성격 특성 목록")
    appearance: Optional[str] = Field(None, description="외모 설명")
    background: Optional[str] = Field(None, description="배경 설명")
    relationships: Optional[Dict[str, Any]] = Field(None, description="다른 캐릭터와의 관계")


class CharacterResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    age: Optional[int]
    personality_traits: Optional[List[str]]
    appearance: Optional[str]
    background: Optional[str]
    relationships: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CharacterListResponse(BaseModel):
    items: List[CharacterResponse]
    total: int
