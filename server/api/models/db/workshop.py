"""ORM model for Workshop templates."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class Workshop(Base):
    """A reusable workshop template managed by admins."""

    __tablename__ = "workshops"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image: Mapped[str] = mapped_column(
        String(500), nullable=False, default="rocker/rstudio:latest"
    )
    default_duration: Mapped[str] = mapped_column(
        String(20), nullable=False, default="4h"
    )
    resources: Mapped[dict] = mapped_column(JSONB, nullable=False)
    storage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ingress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    instances: Mapped[list["WorkshopInstance"]] = relationship(  # noqa: F821
        "WorkshopInstance", back_populates="workshop"
    )
