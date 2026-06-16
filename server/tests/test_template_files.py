"""Validate the git-managed template files in deploy/templates/ (ADR-0006).

This is the CI gate for the YAML template catalog: every deploy/templates/*.yaml
must satisfy the WorkshopTemplateFile schema, and slugs must be unique. No
cluster or database is required.
"""

import pathlib

import pytest
import yaml
from pydantic import ValidationError

from api.models.schemas.workshop_template import WorkshopTemplateFile

_TEMPLATES_DIR = pathlib.Path(__file__).parents[2] / "deploy" / "templates"


def _template_files() -> list[pathlib.Path]:
    return sorted(_TEMPLATES_DIR.glob("*.yaml"))


def test_templates_dir_is_present_and_nonempty():
    assert _TEMPLATES_DIR.is_dir(), f"missing {_TEMPLATES_DIR}"
    assert _template_files(), "no deploy/templates/*.yaml files found"


@pytest.mark.parametrize("path", _template_files(), ids=lambda p: p.name)
def test_template_file_matches_schema(path: pathlib.Path):
    """Each template file must parse as YAML and validate against the schema."""
    data = yaml.safe_load(path.read_text())
    assert isinstance(data, dict), f"{path.name}: top level must be a mapping"
    try:
        WorkshopTemplateFile.model_validate(data)
    except ValidationError as e:  # pragma: no cover - failure path
        pytest.fail(f"{path.name} failed schema validation:\n{e}")


def test_template_slugs_are_unique():
    slugs: dict[str, str] = {}
    for path in _template_files():
        data = yaml.safe_load(path.read_text())
        tmpl = WorkshopTemplateFile.model_validate(data)
        if tmpl.slug in slugs:
            pytest.fail(
                f"duplicate slug {tmpl.slug!r} in {path.name} and {slugs[tmpl.slug]}"
            )
        slugs[tmpl.slug] = path.name


def test_template_filename_matches_slug():
    """Convention: <slug>.yaml — keeps the directory scannable."""
    for path in _template_files():
        tmpl = WorkshopTemplateFile.model_validate(yaml.safe_load(path.read_text()))
        assert path.stem == tmpl.slug, (
            f"{path.name}: filename stem {path.stem!r} != slug {tmpl.slug!r}"
        )
