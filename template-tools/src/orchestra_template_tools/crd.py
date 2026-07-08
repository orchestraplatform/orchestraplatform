"""Typed Workshop CRD contract shared by the server and operator (#51).

Single source of truth for the Workshop CRD identity (group/version/plural/kind)
and the ``spec`` shape declared in
``deploy/charts/orchestra-crds/templates/workshop-crd.yaml``. The server
serializes launches through :class:`WorkshopSpec`
(``model_dump(by_alias=True)``) and the operator parses incoming spec dicts
with ``model_validate``; contract tests on both sides pin the model to the
chart YAML.

The resource/storage sub-models are the very same classes the template schema
uses (:mod:`.models`) — ADR-0006 defines a template as a friendly projection of
the CRD spec — so template<->CRD drift is a type error, not a silent divergence.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import WorkshopResources, WorkshopStorage

GROUP = "orchestra.io"
VERSION = "v1"
PLURAL = "workshops"
KIND = "Workshop"


class WorkshopIngress(BaseModel):
    """Workshop ingress configuration (``spec.ingress``)."""

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


class WorkshopSpec(BaseModel):
    """The Workshop CRD ``spec`` block.

    Field defaults mirror the CRD schema defaults, so a spec dict that already
    passed admission round-trips unchanged. ``owner`` is required by the CRD
    schema but optional here to tolerate legacy CRs created before ownership
    was added (ADR-0002).
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., description="Workshop instance name")
    owner: str | None = Field(
        default=None,
        description="Email address of the workshop owner (set by the API from "
        "the authenticated user)",
    )
    duration: str = Field(default="4h", description="Workshop duration")
    image: str = Field(default="rocker/rstudio:latest", description="Docker image")
    port: int = Field(
        default=8787,
        ge=1,
        le=65535,
        description="Port the application listens on inside the container",
    )
    tier: Literal["small", "large"] = Field(
        default="small", description="Tenant node-pool tier (ADR-0005)"
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Extra environment variables for the app container",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Container args, replacing the image's default CMD",
    )
    resources: WorkshopResources = Field(default_factory=WorkshopResources)
    storage: WorkshopStorage | None = Field(default=None)
    ingress: WorkshopIngress | None = Field(default=None)
