"""Pydantic models for workshop API."""

import re
from datetime import datetime
from enum import Enum
from typing import Literal

# WorkshopResources / WorkshopStorage are defined in orchestra-template-tools,
# the single source of truth for the template schema (ADR-0007). Re-exported here
# so existing ``from api.models.workshop import WorkshopResources`` keeps working.
from orchestra_template_tools import WorkshopResources, WorkshopStorage
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

__all__ = [
    "WorkshopResources",
    "WorkshopStorage",
]


class WorkshopPhase(str, Enum):
    """Workshop lifecycle phases."""

    PENDING = "Pending"
    CREATING = "Creating"
    STARTING = "Starting"
    READY = "Ready"
    RUNNING = "Running"
    TERMINATING = "Terminating"
    FAILED = "Failed"
    # Not emitted by the operator on a CRD; used by the API to mark an
    # instance whose backing CRD has vanished (see workshop_instance_service).
    TERMINATED = "Terminated"


class WorkshopIngress(BaseModel):
    """Workshop ingress configuration."""

    model_config = ConfigDict(populate_by_name=True)

    host: str | None = Field(
        default=None,
        description="Custom ingress hostname. Leave unset to use the environment default.",
    )
    annotations: dict[str, str] = Field(
        default_factory=dict, description="Ingress annotations"
    )

    @field_validator("host", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        return None if v == "" else v


_K8S_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")
_K8S_NAME_MAX = 253


class WorkshopCreate(BaseModel):
    """Request model for creating a workshop."""

    name: str = Field(..., description="Workshop name")
    duration: str = Field(default="4h", description="Workshop duration")
    image: str = Field(default="rocker/rstudio:latest", description="RStudio image")
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
        description="Tenant node-pool tier. The operator maps this to "
        "nodeSelector/tolerations when tenant pools are enabled (ADR-0005/0006).",
    )
    resources: WorkshopResources = Field(default_factory=WorkshopResources)
    storage: WorkshopStorage | None = Field(default=None)
    ingress: WorkshopIngress | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def name_is_valid_k8s(cls, v: str) -> str:
        """Validate that the name is a valid Kubernetes resource name (RFC 1123)."""
        if len(v) > _K8S_NAME_MAX:
            raise ValueError(f"name must be at most {_K8S_NAME_MAX} characters")
        if not _K8S_NAME_RE.match(v):
            raise ValueError(
                "name must consist of lowercase alphanumeric characters or '-', "
                "start and end with an alphanumeric character"
            )
        return v


class WorkshopCondition(BaseModel):
    """Workshop status condition."""

    model_config = ConfigDict(populate_by_name=True)

    type: str
    status: str
    reason: str | None = None
    message: str | None = None
    last_transition_time: datetime | None = Field(
        default=None, alias="lastTransitionTime"
    )


class WorkshopStatus(BaseModel):
    """Workshop status information."""

    model_config = ConfigDict(populate_by_name=True)

    phase: WorkshopPhase
    url: str | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    conditions: list[WorkshopCondition] = Field(default_factory=list)


class WorkshopResponse(BaseModel):
    """Response model for workshop information."""

    name: str
    namespace: str
    owner: EmailStr | None = (
        None  # None for legacy CRs created before ownership was added
    )
    spec: WorkshopCreate
    status: WorkshopStatus | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
