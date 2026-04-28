"""
플롯 포인트 ORM 모델
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
    from backend.app.models.project import Project


class PlotPoint(Base):
    __tablename__ = "plot_points"

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
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    plot_stage: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    sequence_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    is_completed: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    target_chapter: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="plot_points")
