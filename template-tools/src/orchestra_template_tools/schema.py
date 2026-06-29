"""JSON Schema generation for workshop template files.

``template.schema.json`` is generated from :class:`WorkshopTemplateFile` and is
the single source of truth referenced by each template's
``# yaml-language-server: $schema=`` directive for in-editor validation.
"""

import json

from .models import WorkshopTemplateFile

_TITLE = "Orchestra Workshop Template"
_DRAFT = "http://json-schema.org/draft-07/schema#"


def build_schema() -> dict:
    """Return the JSON Schema for a template file (camelCase aliases)."""
    schema = WorkshopTemplateFile.model_json_schema(by_alias=True)
    schema["$schema"] = _DRAFT
    schema["title"] = _TITLE
    return schema


def schema_json() -> str:
    """Return the schema as a trailing-newline-terminated JSON string."""
    return json.dumps(build_schema(), indent=2) + "\n"
