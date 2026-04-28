"""
챕터 및 챕터 버전 ORM 모델
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.project import Project
    from backend.app.models.consistency import ConsistencyIssue
    from backend.app.models.generation_log import GenerationLog
    from backend.app.models.narrative import ForeshadowingElement, ChapterEmotionalArc


class Chapter(Base):
    __tablename__ = "chapters"

    __table_args__ = (
        sa.UniqueConstraint("project_id", "chapter_number", name="unique_chapter_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    chapter_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(sa.String(500), nullable=True)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    word_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    consistency_score: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
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
    is_deleted: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="chapters")
    versions: Mapped[List["ChapterVersion"]] = relationship(
        "ChapterVersion", back_populates="chapter", cascade="all, delete-orphan"
    )
    consistency_issues: Mapped[List["ConsistencyIssue"]] = relationship(
        "ConsistencyIssue", back_populates="chapter", cascade="all, delete-orphan"
    )
    generation_logs: Mapped[List["GenerationLog"]] = relationship(
        "GenerationLog", back_populates="chapter"
    )
    foreshadowing_elements: Mapped[List["ForeshadowingElement"]] = relationship(
        "ForeshadowingElement",
        back_populates="chapter",
        cascade="all, delete-orphan",
        foreign_keys="ForeshadowingElement.chapter_id",
    )
    resolved_foreshadowing: Mapped[List["ForeshadowingElement"]] = relationship(
        "ForeshadowingElement",
        back_populates="resolved_in_chapter",
        foreign_keys="ForeshadowingElement.resolved_in_chapter_id",
    )
    emotional_arc: Mapped[Optional["ChapterEmotionalArc"]] = relationship(
        "ChapterEmotionalArc", back_populates="chapter", cascade="all, delete-orphan"
    )


class ChapterVersion(Base):
    __tablename__ = "chapter_versions"

    __table_args__ = (
        sa.UniqueConstraint("chapter_id", "version_number", name="unique_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    word_count: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", back_populates="versions")
