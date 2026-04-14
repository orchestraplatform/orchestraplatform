"""Pydantic models for workshop API."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback for when pydantic is not installed
    class BaseModel:
        pass
    def Field(*args, **kwargs):
        return None


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
    cpu_request: str = Field(default="500m", description="CPU request", alias="cpuRequest")
    memory_request: str = Field(default="1Gi", description="Memory request", alias="memoryRequest")


class WorkshopStorage(BaseModel):
    """Workshop storage configuration."""
    size: str = Field(default="10Gi", description="Storage size")
    storage_class: Optional[str] = Field(default=None, description="Storage class", alias="storageClass")


class WorkshopIngress(BaseModel):
    """Workshop ingress configuration."""
    host: Optional[str] = Field(default=None, description="Ingress hostname")
    annotations: Dict[str, str] = Field(default_factory=dict, description="Ingress annotations")


class WorkshopCreate(BaseModel):
    """Request model for creating a workshop."""
    name: str = Field(..., description="Workshop name")
    duration: str = Field(default="4h", description="Workshop duration")
    image: str = Field(default="rocker/rstudio:latest", description="RStudio image")
    resources: WorkshopResources = Field(default_factory=WorkshopResources)
    storage: Optional[WorkshopStorage] = Field(default=None)
    ingress: Optional[WorkshopIngress] = Field(default=None)


class WorkshopUpdate(BaseModel):
    """Request model for updating a workshop."""
    duration: Optional[str] = None
    resources: Optional[WorkshopResources] = None


class WorkshopCondition(BaseModel):
    """Workshop status condition."""
    type: str
    status: str
    reason: Optional[str] = None
    message: Optional[str] = None
    last_transition_time: Optional[datetime] = Field(alias="lastTransitionTime")


class WorkshopStatus(BaseModel):
    """Workshop status information."""
    phase: WorkshopPhase
    url: Optional[str] = None
    created_at: Optional[datetime] = Field(alias="createdAt")
    expires_at: Optional[datetime] = Field(alias="expiresAt")
    conditions: List[WorkshopCondition] = Field(default_factory=list)


class WorkshopResponse(BaseModel):
    """Response model for workshop information."""
    name: str
    namespace: str
    spec: WorkshopCreate
    status: Optional[WorkshopStatus] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkshopList(BaseModel):
    """Response model for workshop list."""
    items: List[WorkshopResponse]
    total: int
    page: int = 1
    size: int = 50


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
