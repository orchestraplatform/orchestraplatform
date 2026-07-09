"""Canonical Pydantic models for git-managed workshop templates (ADR-0007).

This module is the **single source of truth** for the workshop-template schema.
The platform API depends on this package and re-exports these models; the
``orchestra-validate-templates`` CLI and the platform's runtime re-validation
both validate against them; and ``template.schema.json`` is generated from
:class:`WorkshopTemplateFile`.

Kept deliberately dependency-light (pydantic only) so a workshop-templates repo
can install it in CI without dragging in the platform's server/operator stack.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

_K8S_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")
_SLUG_MAX = 40

# Closed catalog-tag vocabulary. Seeded from EXACTLY the tags the two shipped
# templates use (deploy/charts/orchestra/files/templates/{rstudio,jupyter}.yaml);
# an unknown tag fails validation everywhere. Extending it is a reviewed PR to
# this enum (ADR-0009) so the issue-form checkboxes and the validator can't drift.
TemplateTag = Literal["bioconductor", "jupyter", "python", "rstudio"]

_URL_ADAPTER = TypeAdapter(HttpUrl)


class WorkshopResources(BaseModel):
    """Workshop resource requirements."""

    model_config = ConfigDict(populate_by_name=True)

    cpu: str = Field(default="1", description="CPU limit")
    memory: str = Field(default="2Gi", description="Memory limit")
    cpu_request: str = Field(
        default="500m", description="CPU request", alias="cpuRequest"
    )
    memory_request: str = Field(
        default="1Gi", description="Memory request", alias="memoryRequest"
    )
    ephemeral_storage: str = Field(
        default="8Gi",
        description=(
            "Ephemeral storage limit. Covers everything written outside the /data "
            "PVC (package installs, /tmp, container writable layer); the kubelet "
            "evicts the pod if exceeded."
        ),
        alias="ephemeralStorage",
    )
    ephemeral_storage_request: str = Field(
        default="8Gi",
        description="Ephemeral storage request",
        alias="ephemeralStorageRequest",
    )


class WorkshopStorage(BaseModel):
    """Workshop storage configuration."""

    model_config = ConfigDict(populate_by_name=True)

    size: str = Field(default="10Gi", description="Storage size")
    storage_class: str | None = Field(
        default=None,
        description="Storage class name. Leave unset to use the cluster default.",
        alias="storageClass",
    )

    @field_validator("storage_class", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: str | None) -> str | None:
        return None if v == "" else v


class WorkshopTemplateCreate(BaseModel):
    """The spec fields shared by a template definition."""

    name: str = Field(..., description="Human-readable display name")
    slug: str = Field(
        ...,
        description="k8s-safe identifier used as prefix for instance names (max 40 chars)",
    )
    description: str | None = Field(
        default=None,
        description="Optional workshop description. Catalog metadata, interpreted "
        "as Markdown (rendered sanitized by the frontend — see #63); never reaches "
        "the CRD.",
    )
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
        description="Tenant scheduling tier, selected by name (small/large). The "
        "operator resolves it against its configured tier map (ADR-0005) to a "
        "nodeSelector / tolerations / compute-class. Unknown or unmapped tiers "
        "schedule anywhere, so this is a cloud-neutral hint, not a hard "
        "requirement.",
    )
    resources: WorkshopResources = Field(default_factory=WorkshopResources)
    storage: WorkshopStorage | None = Field(default=None)
    tags: list[TemplateTag] = Field(
        default_factory=list,
        description="Category tags for filtering, from a closed vocabulary. An "
        "unknown tag fails validation; extend the enum via a reviewed PR.",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("slug")
    @classmethod
    def slug_is_valid(cls, v: str) -> str:
        if len(v) > _SLUG_MAX:
            raise ValueError(f"slug must be at most {_SLUG_MAX} characters")
        if not _K8S_SLUG_RE.match(v):
            raise ValueError(
                "slug must consist of lowercase alphanumeric characters or '-', "
                "start and end with an alphanumeric character"
            )
        return v


class WorkshopTemplateFile(WorkshopTemplateCreate):
    """Schema for a git-managed template YAML file (ADR-0006/0007).

    Extends the spec with an ``enabled`` flag (the declarative replacement for the
    runtime ``isActive`` toggle). This is the validation contract for the
    git-managed template files and the source the in-memory registry loads from.
    ``model_config`` is inherited (``populate_by_name``), so files may use either
    camelCase (``defaultDuration``) or snake_case.
    """

    enabled: bool = Field(
        default=True,
        description="Whether the template is shown in the catalog and launchable. "
        "Set false to retire a template without deleting its file.",
    )
    url: str | None = Field(
        default=None,
        description="Optional URL of the workshop's landing/materials page (catalog "
        "'Learn more' link). Catalog metadata; never reaches the CRD.",
    )
    source_url: str | None = Field(
        default=None,
        alias="sourceUrl",
        description="Optional URL of the repository the workshop content lives in "
        "(catalog 'Source' link). Catalog metadata; never reaches the CRD.",
    )
    submitted_by: str | None = Field(
        default=None,
        alias="submittedBy",
        description="GitHub handle of the last submitter, stamped by the template "
        "front-door Action from the issue author (ADR-0009); absent on hand-authored "
        "templates. Catalog metadata; never reaches the CRD.",
    )

    @field_validator("url", "source_url")
    @classmethod
    def _valid_url(cls, v: str | None) -> str | None:
        if v is not None:
            _URL_ADAPTER.validate_python(v)  # raises if not a valid URL
        return v
