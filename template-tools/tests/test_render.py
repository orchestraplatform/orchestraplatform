"""Tests for form-to-YAML rendering (ADR-0009)."""

import json

from orchestra_template_tools import (
    existing_template_path,
    load_template,
    render_submission,
    validate_documents,
)
from orchestra_template_tools.cli import render_main

SUBMISSION = {
    "name": "RStudio (Bioconductor)",
    "slug": "rstudio",
    "description": "RStudio Server on the Bioconductor base image.",
    "image": "bioconductor/bioconductor_docker:RELEASE_3_20",
    "defaultDuration": "4h",
    "port": 8787,
    "tier": "small",
    "resources": {"cpu": "2", "memory": "4Gi"},
    "storage": {"size": "10Gi"},
    "tags": ["bioconductor", "rstudio"],
    "enabled": True,
}


def test_valid_submission_renders_yaml():
    result = render_submission(SUBMISSION)
    assert result.ok
    assert result.errors == []
    assert result.template.slug == "rstudio"
    assert result.yaml_text.startswith(
        "# yaml-language-server: $schema=./template.schema.json\n"
    )


def test_yaml_round_trips_through_validator():
    result = render_submission(SUBMISSION)
    catalog = validate_documents({"rstudio.yaml": result.yaml_text})
    assert catalog.ok
    assert catalog.templates[0] == result.template


def test_yaml_is_deterministic():
    # Same fields, different key order -> byte-identical output.
    reordered = dict(reversed(list(SUBMISSION.items())))
    assert render_submission(SUBMISSION).yaml_text == (
        render_submission(reordered).yaml_text
    )


def test_defaults_materialized_and_camelcase():
    text = render_submission({"name": "X", "slug": "x"}).yaml_text
    # Defaults from the shared model are written out explicitly.
    assert "defaultDuration: 4h" in text
    assert "ephemeralStorage: 8Gi" in text
    assert "enabled: true" in text


def test_empty_fields_omitted():
    text = render_submission({"name": "X", "slug": "x"}).yaml_text
    for absent in ("description", "env", "args", "tags", "storage"):
        assert f"{absent}:" not in text


def test_env_keys_sorted():
    text = render_submission(
        {"name": "X", "slug": "x", "env": {"ZZZ": "1", "AAA": "2"}}
    ).yaml_text
    assert text.index("AAA") < text.index("ZZZ")
    assert load_template(text).env == {"AAA": "2", "ZZZ": "1"}


def test_invalid_submission_field_level_errors():
    result = render_submission({"slug": "Bad_Slug", "port": 99999})
    assert not result.ok
    assert result.yaml_text is None
    locs = {e.split(":")[0] for e in result.errors}
    assert {"name", "slug", "port"} <= locs


def test_non_object_submission_is_error_not_exception():
    result = render_submission(["not", "a", "dict"])
    assert not result.ok
    assert result.errors == ["<root>: submission must be a JSON object"]


def test_existing_template_path(tmp_path):
    (tmp_path / "rstudio.yaml").write_text("name: X\nslug: rstudio\n")
    (tmp_path / "jupyter.yml").write_text("name: Y\nslug: jupyter\n")
    assert existing_template_path("rstudio", tmp_path) == tmp_path / "rstudio.yaml"
    assert existing_template_path("jupyter", tmp_path) == tmp_path / "jupyter.yml"
    assert existing_template_path("new-slug", tmp_path) is None


def _run_cli(tmp_path, capsys, submission, *extra):
    src = tmp_path / "submission.json"
    src.write_text(json.dumps(submission))
    rc = render_main([str(src), *extra])
    return rc, json.loads(capsys.readouterr().out)


def test_cli_valid_submission(tmp_path, capsys):
    rc, out = _run_cli(tmp_path, capsys, SUBMISSION)
    assert rc == 0
    assert out["ok"] is True
    assert out["slug"] == "rstudio"
    assert out["yaml"].startswith("# yaml-language-server")
    assert out["exists"] is None  # no --templates-dir given


def test_cli_create_vs_update(tmp_path, capsys):
    tdir = tmp_path / "templates"
    tdir.mkdir()
    rc, out = _run_cli(tmp_path, capsys, SUBMISSION, "--templates-dir", str(tdir))
    assert rc == 0
    assert out["exists"] is False
    assert out["path"] == str(tdir / "rstudio.yaml")

    (tdir / "rstudio.yaml").write_text(out["yaml"])
    rc, out = _run_cli(tmp_path, capsys, SUBMISSION, "--templates-dir", str(tdir))
    assert out["exists"] is True
    assert out["path"] == str(tdir / "rstudio.yaml")


def test_cli_invalid_submission_returns_1(tmp_path, capsys):
    rc, out = _run_cli(tmp_path, capsys, {"slug": "x"})  # missing name
    assert rc == 1
    assert out["ok"] is False
    assert out["yaml"] is None
    assert any(e.startswith("name:") for e in out["errors"])


def test_cli_invalid_json_returns_1(tmp_path, capsys):
    src = tmp_path / "bad.json"
    src.write_text("{not json")
    rc = render_main([str(src)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert any("invalid JSON" in e for e in out["errors"])


def test_cli_missing_file_returns_2(tmp_path):
    assert render_main([str(tmp_path / "nope.json")]) == 2
