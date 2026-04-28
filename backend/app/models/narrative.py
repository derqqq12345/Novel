"""
내러티브 아크 관련 ORM 모델 (복선, 감정 곡선)
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
    from backend.app.models.project import Project
    from backend.app.models.chapter import Chapter


class ForeshadowingElement(Base):
    __tablename__ = "foreshadowing_elements"

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
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("chapters.id", ondelete="CASCADE"),
        nullable=False,
    )
    text_excerpt: Mapped[str] = mapped_column(sa.Text, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    resolved_in_chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("chapters.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="foreshadowing_elements",
        foreign_keys=[project_id],
    )
    chapter: Mapped["Chapter"] = relationship(
        "Chapter",
        back_populates="foreshadowing_elements",
        foreign_keys=[chapter_id],
    )
    resolved_in_chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter",
        back_populates="resolved_foreshadowing",
        foreign_keys=[resolved_in_chapter_id],
    )


class ChapterEmotionalArc(Base):
    __tablename__ = "chapter_emotional_arcs"

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
    overall_intensity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    tension_curve: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dominant_emotion: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    narrative_cohesion_score: Mapped[Optional[float]] = mapped_column(
        sa.Float, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    chapter: Mapped["Chapter"] = relationship(
        "Chapter", back_populates="emotional_arc"
    )
