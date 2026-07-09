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
from .forms import (
    FormParseError,
    parse_args,
    parse_env,
    parse_issue_body,
    submission_from_issue_body,
)
from .models import (
    TemplateTag,
    WorkshopResources,
    WorkshopStorage,
    WorkshopTemplateCreate,
    WorkshopTemplateFile,
    WorkspaceStorage,
)
from .presets import SIZE_NAMES, SIZE_PRESETS
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
    "FormParseError",
    "RenderResult",
    "SIZE_NAMES",
    "SIZE_PRESETS",
    "TemplateTag",
    "WorkshopIngress",
    "WorkshopResources",
    "WorkshopSpec",
    "WorkshopStorage",
    "WorkshopTemplateCreate",
    "WorkshopTemplateFile",
    "WorkspaceStorage",
    "build_schema",
    "existing_template_path",
    "load_template",
    "parse_args",
    "parse_env",
    "parse_issue_body",
    "render_submission",
    "render_yaml",
    "schema_json",
    "submission_from_issue_body",
    "validate_documents",
]
