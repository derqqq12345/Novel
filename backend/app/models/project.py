"""
프로젝트 ORM 모델
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.chapter import Chapter
    from backend.app.models.character import Character
    from backend.app.models.plot import PlotPoint
    from backend.app.models.worldbuilding import WorldBuilding
    from backend.app.models.narrative import ForeshadowingElement


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    genre: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    total_word_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), default="active", nullable=False)
    ai_model: Mapped[str] = mapped_column(sa.String(50), default="qwen", nullable=False)
    ai_model_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False, server_default=sa.text("'{}'::jsonb")
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="projects")
    chapters: Mapped[List["Chapter"]] = relationship(
        "Chapter", back_populates="project", cascade="all, delete-orphan"
    )
    characters: Mapped[List["Character"]] = relationship(
        "Character", back_populates="project", cascade="all, delete-orphan"
    )
    plot_points: Mapped[List["PlotPoint"]] = relationship(
        "PlotPoint", back_populates="project", cascade="all, delete-orphan"
    )
    world_buildings: Mapped[List["WorldBuilding"]] = relationship(
        "WorldBuilding", back_populates="project", cascade="all, delete-orphan"
    )
    foreshadowing_elements: Mapped[List["ForeshadowingElement"]] = relationship(
        "ForeshadowingElement",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="ForeshadowingElement.project_id",
    )
