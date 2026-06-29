"""Orchestra workshop-template schema, validation, and CLI (ADR-0007).

The single source of truth for the workshop-template contract, shared by the
platform API (which depends on this package), the ``orchestra-validate-templates``
CLI, and the workshop-templates repo's CI.
"""

from .models import (
    WorkshopResources,
    WorkshopStorage,
    WorkshopTemplateCreate,
    WorkshopTemplateFile,
)
from .schema import build_schema, schema_json
from .validate import (
    CatalogResult,
    FileResult,
    load_template,
    validate_documents,
)

__all__ = [
    "CatalogResult",
    "FileResult",
    "WorkshopResources",
    "WorkshopStorage",
    "WorkshopTemplateCreate",
    "WorkshopTemplateFile",
    "build_schema",
    "load_template",
    "schema_json",
    "validate_documents",
]
