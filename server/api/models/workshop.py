"""Pydantic models for workshop API."""

import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


class WorkshopPhase(str, Enum):
    """Workshop lifecycle phases."""

    PENDING = "Pending"
    CREATING = "Creating"
    READY = "Ready"
    RUNNING = "Running"
    TERMINATING = "Terminating"
    FAILED = "Failed"


class WorkshopResources(BaseModel):
    """Workshop resource requirements."""

    cpu: str = Field(default="1", description="CPU limit")
    memory: str = Field(default="2Gi", description="Memory limit")
    cpu_request: str = Field(
        default="500m", description="CPU request", alias="cpuRequest"
    )
    memory_request: str = Field(
        default="1Gi", description="Memory request", alias="memoryRequest"
    )


class WorkshopStorage(BaseModel):
    """Workshop storage configuration."""

    size: str = Field(default="10Gi", description="Storage size")
    storage_class: str | None = Field(
        default=None, description="Storage class name. Leave unset to use the cluster default.", alias="storageClass"
    )

    @field_validator("storage_class", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        return None if v == "" else v


class WorkshopIngress(BaseModel):
    """Workshop ingress configuration."""

    host: str | None = Field(
        default=None, description="Custom ingress hostname. Leave unset to use the environment default."
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


class WorkshopUpdate(BaseModel):
    """Request model for updating a workshop."""

    duration: str | None = None
    resources: WorkshopResources | None = None


class WorkshopCondition(BaseModel):
    """Workshop status condition."""

    type: str
    status: str
    reason: str | None = None
    message: str | None = None
    last_transition_time: datetime | None = Field(alias="lastTransitionTime")


class WorkshopStatus(BaseModel):
    """Workshop status information."""

    phase: WorkshopPhase
    url: str | None = None
    created_at: datetime | None = Field(alias="createdAt")
    expires_at: datetime | None = Field(alias="expiresAt")
    conditions: list[WorkshopCondition] = Field(default_factory=list)


class WorkshopResponse(BaseModel):
    """Response model for workshop information."""

    name: str
    namespace: str
    owner: EmailStr
    spec: WorkshopCreate
    status: WorkshopStatus | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkshopList(BaseModel):
    """Response model for workshop list."""

    items: list[WorkshopResponse]
    total: int
    page: int = 1
    size: int = 50


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    error_code: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
