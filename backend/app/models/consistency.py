"""
일관성 이슈 ORM 모델
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.database import Base

if TYPE_CHECKING:
    from backend.app.models.chapter import Chapter


class ConsistencyIssue(Base):
    __tablename__ = "consistency_issues"

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
    issue_type: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    line_number: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    is_resolved: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    # Relationships
    chapter: Mapped["Chapter"] = relationship(
        "Chapter", back_populates="consistency_issues"
    )
