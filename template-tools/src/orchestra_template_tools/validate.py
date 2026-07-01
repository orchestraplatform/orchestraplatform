"""Validation of workshop-template documents.

Pure, I/O-light: callers supply a mapping of ``filename -> file text`` and get
back per-file results plus catalog-level checks (unique slugs, filename matches
slug). The same routine backs three call sites — the ``orchestra-validate-
templates`` CLI, the templates repo's CI, and the platform's runtime
re-validation (ADR-0007 decision E) — so they can never silently disagree.

This module intentionally does no network or filesystem fetching: the platform
fetches over a UPath source and hands the text in; the CLI reads a local dir.
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field

import yaml
from pydantic import ValidationError

from .models import WorkshopTemplateFile


@dataclass
class FileResult:
    """Outcome of validating a single template document."""

    name: str
    ok: bool
    errors: list[str] = field(default_factory=list)
    template: WorkshopTemplateFile | None = None


@dataclass
class CatalogResult:
    """Aggregate outcome of validating a set of template documents."""

    files: list[FileResult]
    errors: list[str] = field(default_factory=list)  # catalog-level errors

    @property
    def ok(self) -> bool:
        return not self.errors and all(f.ok for f in self.files)

    @property
    def templates(self) -> list[WorkshopTemplateFile]:
        """Validated templates, in input order (only meaningful when ``ok``)."""
        return [f.template for f in self.files if f.template is not None]


def load_template(text: str) -> WorkshopTemplateFile:
    """Parse and validate one template document, raising on any error."""
    data = yaml.safe_load(text)
    return WorkshopTemplateFile.model_validate(data)


def _filename_stem(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    for suffix in (".yaml", ".yml"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def validate_documents(docs: Mapping[str, str]) -> CatalogResult:
    """Validate a mapping of ``name -> YAML text``.

    Per file: parses and validates against :class:`WorkshopTemplateFile`.
    Catalog-level: rejects empty input, duplicate slugs, and a filename that does
    not match its template ``slug`` (``<slug>.yaml`` convention).
    """
    files: list[FileResult] = []
    catalog_errors: list[str] = []

    for name in sorted(docs):
        text = docs[name]
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            files.append(
                FileResult(name=name, ok=False, errors=[f"invalid YAML: {exc}"])
            )
            continue
        if data is None:
            files.append(FileResult(name=name, ok=False, errors=["file is empty"]))
            continue
        try:
            tmpl = WorkshopTemplateFile.model_validate(data)
        except ValidationError as exc:
            files.append(
                FileResult(
                    name=name,
                    ok=False,
                    errors=[_format_error(e) for e in exc.errors()],
                )
            )
            continue

        errors: list[str] = []
        stem = _filename_stem(name)
        if stem != tmpl.slug:
            errors.append(
                f"filename stem '{stem}' does not match slug '{tmpl.slug}' "
                "(expected <slug>.yaml)"
            )
        files.append(FileResult(name=name, ok=not errors, errors=errors, template=tmpl))

    if not docs:
        catalog_errors.append("no template files found")

    # Duplicate slugs across the valid files.
    slugs = [f.template.slug for f in files if f.template is not None]
    for slug, count in Counter(slugs).items():
        if count > 1:
            catalog_errors.append(f"duplicate slug '{slug}' across {count} files")

    return CatalogResult(files=files, errors=catalog_errors)


def _format_error(err: dict) -> str:
    loc = ".".join(str(p) for p in err.get("loc", ())) or "<root>"
    return f"{loc}: {err.get('msg', 'invalid')}"
