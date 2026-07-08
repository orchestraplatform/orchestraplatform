"""Orchestra workshop-template schema, validation, and CLI (ADR-0007).

The single source of truth for the workshop-template contract, shared by the
platform API (which depends on this package), the ``orchestra-validate-templates``
CLI, and the workshop-templates repo's CI.
"""

from .crd import (
    GROUP,
    KIND,
    PLURAL,
    VERSION,
    WorkshopIngress,
    WorkshopSpec,
)
from .models import (
    WorkshopResources,
    WorkshopStorage,
    WorkshopTemplateCreate,
    WorkshopTemplateFile,
)
from .render import (
    RenderResult,
    existing_template_path,
    render_submission,
    render_yaml,
)
from .schema import build_schema, schema_json
from .validate import (
    CatalogResult,
    FileResult,
    load_template,
    validate_documents,
)

__all__ = [
    "GROUP",
    "KIND",
    "PLURAL",
    "VERSION",
    "CatalogResult",
    "FileResult",
    "RenderResult",
    "WorkshopIngress",
    "WorkshopResources",
    "WorkshopSpec",
    "WorkshopStorage",
    "WorkshopTemplateCreate",
    "WorkshopTemplateFile",
    "build_schema",
    "existing_template_path",
    "load_template",
    "render_submission",
    "render_yaml",
    "schema_json",
    "validate_documents",
]
