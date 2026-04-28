"""
생성 로그 ORM 모델
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.chapter import Chapter
    from backend.app.models.user import User


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("chapters.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_time_ms: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    consistency_score: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    chapter: Mapped[Optional["Chapter"]] = relationship(
        "Chapter", back_populates="generation_logs"
    )
    user: Mapped["User"] = relationship("User", back_populates="generation_logs")
