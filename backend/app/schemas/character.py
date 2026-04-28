"""
캐릭터 Pydantic 스키마 (DTO)
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CharacterCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    age: Optional[int] = None
    personality_traits: List[str] = []
    appearance: Optional[str] = None
    background: Optional[str] = None
    relationships: Dict[str, str] = {}


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    personality_traits: Optional[List[str]] = None
    appearance: Optional[str] = None
    background: Optional[str] = None
    relationships: Optional[Dict[str, Any]] = None


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
