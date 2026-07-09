"""Form-to-YAML rendering for template submissions (ADR-0009).

The pure core the issue-form front-door Action calls: a structured submission
(parsed issue-form fields as a dict) is validated against the shared models
and rendered as canonical, deterministic template YAML. Invalid input comes
back as field-level error messages, never an exception. The only I/O is the
create-vs-update lookup helper.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import WorkshopTemplateFile
from .presets import SIZE_NAMES, SIZE_PRESETS
from .validate import _format_error

# Matches the header on the hand-authored files in
# deploy/charts/orchestra/files/templates/ so bot-generated files diff cleanly.
_SCHEMA_DIRECTIVE = "# yaml-language-server: $schema=./template.schema.json\n"


class _Dumper(yaml.SafeDumper):
    """SafeDumper that indents sequence items, matching the hand-authored files."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


@dataclass
class RenderResult:
    """Outcome of rendering a template submission."""

    ok: bool
    errors: list[str] = field(default_factory=list)
    template: WorkshopTemplateFile | None = None
    yaml_text: str | None = None


def render_submission(data: object) -> RenderResult:
    """Validate a parsed submission and render it as canonical YAML.

    Never raises on bad input: errors are field-level ``loc: message`` strings
    suitable for posting verbatim as a GitHub issue comment.
    """
    if not isinstance(data, Mapping):
        return RenderResult(
            ok=False, errors=["<root>: submission must be a JSON object"]
        )
    data = dict(data)
    if "size" in data:
        # `size` is a front-door input only (ADR-0009): expand it to explicit
        # tier + resources — size takes precedence over any supplied values —
        # so the generated YAML carries concrete resources and the model never
        # sees `size`.
        size = data.pop("size")
        preset = SIZE_PRESETS.get(size) if isinstance(size, str) else None
        if preset is None:
            return RenderResult(
                ok=False,
                errors=[
                    f"size: unknown size {size!r}; expected one of "
                    f"{', '.join(SIZE_NAMES)}"
                ],
            )
        data["tier"] = preset["tier"]
        data["resources"] = dict(preset["resources"])  # type: ignore[arg-type]
    try:
        tmpl = WorkshopTemplateFile.model_validate(data)
    except ValidationError as exc:
        return RenderResult(ok=False, errors=[_format_error(e) for e in exc.errors()])
    return RenderResult(ok=True, template=tmpl, yaml_text=render_yaml(tmpl))


def render_yaml(template: WorkshopTemplateFile) -> str:
    """Render a validated template as canonical, deterministic YAML.

    Model field order, camelCase aliases, defaults materialized, unset/empty
    fields omitted, ``env`` keys sorted — identical input always yields an
    identical string, so bot PR diffs stay clean.
    """
    data = template.model_dump(by_alias=True, exclude_none=True)
    data = {k: v for k, v in data.items() if v not in ({}, [])}
    if "env" in data:
        data["env"] = dict(sorted(data["env"].items()))
    body = yaml.dump(
        data,
        Dumper=_Dumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )
    return _SCHEMA_DIRECTIVE + body


def existing_template_path(slug: str, directory: Path) -> Path | None:
    """Return the existing template file for ``slug`` in ``directory``, if any.

    ``None`` means the submission creates a new template; a path means it
    updates that file.
    """
    for suffix in (".yaml", ".yml"):
        path = directory / f"{slug}{suffix}"
        if path.is_file():
            return path
    return None
