"""Pydantic schemas for Workshop templates."""

import re
import uuid
from datetime import datetime
from typing import Literal

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
    port: int = Field(
        default=8787,
        ge=1,
        le=65535,
        description="Port the application listens on inside the container "
        "(e.g. 8787 for RStudio, 8888 for JupyterLab)",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Extra environment variables for the app container "
        "(name -> value). Override operator defaults such as DISABLE_AUTH.",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Container args, replacing the image's default CMD "
        "(e.g. JupyterLab launch flags). Leave empty to use the image default.",
    )
    tier: Literal["small", "large"] = Field(
        default="small",
        description="Tenant node-pool tier (small/large). Maps to "
        "nodeSelector/tolerations in the operator when tenant pools are enabled.",
    )
    resources: WorkshopResources = Field(default_factory=WorkshopResources)
    storage: WorkshopStorage | None = Field(default=None)
    tags: list[str] = Field(
        default_factory=list, description="Category tags for filtering"
    )

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
    port: int | None = Field(default=None, ge=1, le=65535)
    env: dict[str, str] | None = None
    args: list[str] | None = None
    tier: Literal["small", "large"] | None = None
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
    port: int = 8787
    env: dict[str, str] = Field(default_factory=dict)
    args: list[str] = Field(default_factory=list)
    tier: Literal["small", "large"] = "small"
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


class WorkshopTemplateFile(WorkshopTemplateCreate):
    """Schema for a git-managed template YAML file (ADR-0006).

    Extends the create payload with an ``enabled`` flag (the declarative
    replacement for the runtime ``isActive`` toggle). This is the validation
    contract for ``deploy/templates/*.yaml`` and the source the in-memory
    registry loads from. ``model_config`` is inherited (``populate_by_name``),
    so files may use either camelCase (``defaultDuration``) or snake_case.
    """

    enabled: bool = Field(
        default=True,
        description="Whether the template is shown in the catalog and launchable. "
        "Set false to retire a template without deleting its file.",
    )


class WorkshopLaunchRequest(BaseModel):
    """Request body for launching a workshop instance from a template."""

    duration: str | None = Field(
        default=None,
        description="Override the template's default duration (e.g. '2h'). "
        "If omitted, the template default is used.",
    )
    namespace: str | None = Field(default=None, description="Kubernetes namespace")
