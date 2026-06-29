"""Emit the JSON Schema for git-managed template files (ADR-0007).

Writes ``deploy/charts/orchestra/files/templates/template.schema.json`` from the
schema owned by orchestra-template-tools (the single source of truth). Each
template ``*.yaml`` references it via a ``# yaml-language-server: $schema=``
directive so editors validate as you type. The same schema is available from the
CLI via ``orchestra-validate-templates --print-schema``.

Usage:
    uv run python generate_template_schema.py
"""

import pathlib

from orchestra_template_tools import schema_json

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
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(schema_json())
    print(f"✅ Template JSON Schema written: {_OUT}")


if __name__ == "__main__":
    main()
