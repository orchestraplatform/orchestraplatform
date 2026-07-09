"""Pydantic schemas for WorkshopInstance."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from api.models.workshop import WorkshopPhase


class WorkshopInstanceResponse(BaseModel):
    """Response schema for a single workshop instance."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    workshop_id: uuid.UUID = Field(alias="workshopId")
    workshop_name: str | None = Field(
        default=None,
        alias="workshopName",
        description="Display name of the source template (stamped at launch)",
    )
    template_slug: str = Field(
        alias="templateSlug",
        description="Slug of the source template, stamped at launch.",
    )
    resolved_spec: dict[str, Any] = Field(
        default_factory=dict,
        alias="resolvedSpec",
        description="Immutable snapshot of the resolved spec this instance "
        "launched with (image, port, duration, env, args, resources, storage).",
    )
    k8s_name: str = Field(alias="k8sName")
    namespace: str
    owner_email: str = Field(alias="ownerEmail")
    phase: WorkshopPhase
    url: str | None = None
    duration_requested: str = Field(alias="durationRequested")
    launched_at: datetime = Field(alias="launchedAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    terminated_at: datetime | None = Field(default=None, alias="terminatedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class LaunchConflict(BaseModel):
    """409 body when the caller already has an active session of a
    persistence-enabled workshop (ADR-0010 decision F).

    The client offers Continue (use ``instance``) or Start fresh (relaunch
    with ``replaceExisting=true``).
    """

    error: Literal["active_session_exists"] = Field(
        description="Machine-readable discriminator for the conflict body."
    )
    instance: WorkshopInstanceResponse


class InstanceSummary(BaseModel):
    """Aggregate launch counts across all instances."""

    model_config = ConfigDict(populate_by_name=True)

    total_launches: int = Field(alias="totalLaunches")
    launched_last_7_days: int = Field(alias="launchedLast7Days")


class WorkshopInstanceList(BaseModel):
    """Paginated list of workshop instances."""

    items: list[WorkshopInstanceResponse]
    total: int
    page: int = 1
    size: int = 50


class WorkshopInstanceStatus(BaseModel):
    """Lightweight status/URL response for a workshop instance."""

    id: uuid.UUID
    k8s_name: str = Field(alias="k8sName")
    phase: WorkshopPhase
    url: str | None = None
    expires_at: datetime | None = Field(default=None, alias="expiresAt")

    model_config = ConfigDict(populate_by_name=True)


class InstanceUtilization(BaseModel):
    """Time-in-phase utilization breakdown for a single instance."""

    model_config = ConfigDict(populate_by_name=True)

    instance_id: uuid.UUID = Field(alias="instanceId")
    k8s_name: str = Field(alias="k8sName")
    launched_at: datetime = Field(alias="launchedAt")
    terminated_at: datetime | None = Field(default=None, alias="terminatedAt")
    total_elapsed_seconds: int = Field(
        alias="totalElapsedSeconds",
        description="Wall-clock seconds from launch to now (or termination).",
    )
    active_seconds: int = Field(
        alias="activeSeconds",
        description="Seconds spent in Ready or Running phase.",
    )
    phase_seconds: dict[str, int] = Field(
        alias="phaseSeconds",
        description="Seconds spent in each phase, keyed by phase name.",
    )


class TemplateStats(BaseModel):
    """Aggregate utilization statistics for a workshop template."""

    model_config = ConfigDict(populate_by_name=True)

    template_id: uuid.UUID = Field(alias="templateId")
    total_launches: int = Field(alias="totalLaunches")
    active_instances: int = Field(alias="activeInstances")
    total_active_seconds: int = Field(
        alias="totalActiveSeconds",
        description="Sum of active_seconds across all instances of this template.",
    )
    unique_users: int = Field(alias="uniqueUsers")
