"""Pydantic schemas for WorkshopInstance."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkshopInstanceResponse(BaseModel):
    """Response schema for a single workshop instance."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    workshop_id: uuid.UUID = Field(alias="workshopId")
    workshop_name: str | None = Field(
        default=None,
        alias="workshopName",
        description="Display name of the source template",
    )
    k8s_name: str = Field(alias="k8sName")
    namespace: str
    owner_email: str = Field(alias="ownerEmail")
    phase: str
    url: str | None = None
    duration_requested: str = Field(alias="durationRequested")
    launched_at: datetime = Field(alias="launchedAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    terminated_at: datetime | None = Field(default=None, alias="terminatedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


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
    phase: str
    url: str | None = None
    expires_at: datetime | None = Field(default=None, alias="expiresAt")

    model_config = ConfigDict(populate_by_name=True)
