"""ORM models for WorkshopInstance and InstanceEvent."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base


class WorkshopInstance(Base):
    """A single running instance launched from a Workshop template."""

    __tablename__ = "workshop_instances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workshop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workshops.id"), nullable=False
    )
    k8s_name: Mapped[str] = mapped_column(String(253), nullable=False)
    namespace: Mapped[str] = mapped_column(
        String(63), nullable=False, default="default"
    )
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)
    phase: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_requested: Mapped[str] = mapped_column(String(20), nullable=False)
    launched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    terminated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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

    workshop: Mapped["Workshop"] = relationship(  # noqa: F821
        "Workshop", back_populates="instances"
    )
    events: Mapped[list["InstanceEvent"]] = relationship(
        "InstanceEvent", back_populates="instance", order_by="InstanceEvent.recorded_at"
    )


class InstanceEvent(Base):
    """Phase transition event for a WorkshopInstance (used for utilization tracking)."""

    __tablename__ = "instance_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workshop_instances.id"), nullable=False
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    instance: Mapped["WorkshopInstance"] = relationship(
        "WorkshopInstance", back_populates="events"
    )
