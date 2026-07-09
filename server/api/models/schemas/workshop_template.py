"""Pydantic schemas for Workshop templates.

The template *contract* — ``WorkshopTemplateCreate`` and ``WorkshopTemplateFile``
plus the nested ``WorkshopResources`` / ``WorkshopStorage`` — lives in
orchestra-template-tools (ADR-0007), the single source of truth shared by the
API, the CLI, and the workshop-templates repo's CI. They are re-exported here so
the rest of the API can keep importing them from this module. The API-only
response/update/list/launch shapes stay below.
"""

import uuid
from datetime import datetime
from typing import Literal

from orchestra_template_tools import (
    TemplateTag,
    WorkshopTemplateCreate,
    WorkshopTemplateFile,
)
from pydantic import BaseModel, ConfigDict, Field

from api.models.workshop import WorkshopResources, WorkshopStorage

__all__ = [
    "WorkshopLaunchRequest",
    "WorkshopResources",
    "WorkshopStorage",
    "WorkshopTemplateCreate",
    "WorkshopTemplateFile",
    "WorkshopTemplateList",
    "WorkshopTemplateResponse",
    "WorkshopTemplateUpdate",
]


class WorkshopTemplateUpdate(BaseModel):
    """Request body for updating a workshop template (admin only)."""

    name: str | None = None
    description: str | None = None
    image: str | None = None
    default_duration: str | None = Field(default=None, alias="defaultDuration")
    port: int | None = Field(default=None, ge=1, le=65535)
    env: dict[str, str] | None = None
    args: list[str] | None = None
    tier: Literal["small", "large"] | None = None
    resources: WorkshopResources | None = None
    storage: WorkshopStorage | None = None
    tags: list[TemplateTag] | None = None
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
    port: int = 8787
    env: dict[str, str] = Field(default_factory=dict)
    args: list[str] = Field(default_factory=list)
    tier: Literal["small", "large"] = "small"
    resources: WorkshopResources
    storage: WorkshopStorage | None = None
    tags: list[TemplateTag] = Field(default_factory=list)
    url: str | None = None
    source_url: str | None = Field(default=None, alias="sourceUrl")
    submitted_by: str | None = Field(default=None, alias="submittedBy")
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
