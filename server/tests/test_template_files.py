"""Validate the in-chart template files via the shared validator (ADR-0007).

Guards the templates still bundled in the chart (`deploy/charts/orchestra/files/
templates/`) against the same `orchestra_template_tools.validate_documents`
routine the CLI and runtime use, so there is one validation implementation, not
a copy that can drift. (The catalog moves to the external workshop-templates repo
in a later ADR-0007 phase; this guard goes with it.)
"""

import pathlib

from orchestra_template_tools import validate_documents

_TEMPLATES_DIR = (
    pathlib.Path(__file__).parents[2]
    / "deploy"
    / "charts"
    / "orchestra"
    / "files"
    / "templates"
)


def _docs() -> dict[str, str]:
    return {p.name: p.read_text() for p in sorted(_TEMPLATES_DIR.glob("*.yaml"))}


def test_in_chart_templates_validate():
    assert _TEMPLATES_DIR.is_dir(), f"missing {_TEMPLATES_DIR}"
    result = validate_documents(_docs())
    assert result.ok, "in-chart templates failed validation:\n" + "\n".join(
        [f"{f.name}: {e}" for f in result.files for e in f.errors] + result.errors
    )
    assert {t.slug for t in result.templates} >= {"jupyter", "rstudio"}
