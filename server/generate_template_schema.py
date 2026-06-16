"""Emit the JSON Schema for git-managed template files (ADR-0006).

Writes ``deploy/templates/template.schema.json`` from the ``WorkshopTemplateFile``
Pydantic model. Each ``deploy/templates/*.yaml`` references it via a
``# yaml-language-server: $schema=`` directive so editors validate as you type.

Usage:
    uv run python generate_template_schema.py
"""

import json
import pathlib

from api.models.schemas.workshop_template import WorkshopTemplateFile

_OUT = (
    pathlib.Path(__file__).parent.parent
    / "deploy"
    / "charts"
    / "orchestra"
    / "files"
    / "templates"
    / "template.schema.json"
)


def main() -> None:
    schema = WorkshopTemplateFile.model_json_schema(by_alias=True)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "Orchestra Workshop Template"
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"✅ Template JSON Schema written: {_OUT}")


if __name__ == "__main__":
    main()
