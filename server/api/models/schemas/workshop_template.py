"""Pydantic schemas for Workshop templates."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.models.workshop import WorkshopResources, WorkshopStorage

_K8S_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")


class WorkshopTemplateCreate(BaseModel):
    """Request body for creating a workshop template (admin only)."""

    name: str = Field(..., description="Human-readable display name")
    slug: str = Field(
        ...,
        description="k8s-safe identifier used as prefix for instance names (max 40 chars)",
    )
    description: str | None = Field(default=None, description="Optional description")
    image: str = Field(
        default="rocker/rstudio:latest", description="Default Docker image"
    )
    default_duration: str = Field(
        default="4h", alias="defaultDuration", description="Default session duration"
    )
    resources: WorkshopResources = Field(
        default_factory=WorkshopResources
    )
    storage: WorkshopStorage | None = Field(default=None)
    tags: list[str] = Field(default_factory=list, description="Category tags for filtering")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("slug")
    @classmethod
    def slug_is_valid(cls, v: str) -> str:
        if len(v) > 40:
            raise ValueError("slug must be at most 40 characters")
        if not _K8S_SLUG_RE.match(v):
            raise ValueError(
                "slug must consist of lowercase alphanumeric characters or '-', "
                "start and end with an alphanumeric character"
            )
        return v


class WorkshopTemplateUpdate(BaseModel):
    """Request body for updating a workshop template (admin only)."""

    name: str | None = None
    description: str | None = None
    image: str | None = None
    default_duration: str | None = Field(default=None, alias="defaultDuration")
    resources: WorkshopResources | None = None
    storage: WorkshopStorage | None = None
    tags: list[str] | None = None
    is_active: bool | None = Field(default=None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class WorkshopTemplateResponse(BaseModel):
    """Response schema for a workshop template."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    image: str
    default_duration: str = Field(alias="defaultDuration")
    resources: WorkshopResources
    storage: WorkshopStorage | None = None
    tags: list[str] = Field(default_factory=list)
    is_active: bool = Field(alias="isActive")
    created_by: str = Field(alias="createdBy")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class WorkshopTemplateList(BaseModel):
    """Paginated list of workshop templates."""

    items: list[WorkshopTemplateResponse]
    total: int
    page: int = 1
    size: int = 50


class WorkshopLaunchRequest(BaseModel):
    """Request body for launching a workshop instance from a template."""

    duration: str | None = Field(
        default=None,
        description="Override the template's default duration (e.g. '2h'). "
        "If omitted, the template default is used.",
    )
    namespace: str | None = Field(default=None, description="Kubernetes namespace")
