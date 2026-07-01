"""Tests for the shared template validation routine and CLI."""

import textwrap

from orchestra_template_tools import (
    build_schema,
    load_template,
    validate_documents,
)
from orchestra_template_tools.cli import main as cli_main

RSTUDIO = textwrap.dedent(
    """
    name: RStudio (Bioconductor)
    slug: rstudio
    image: bioconductor/bioconductor_docker:RELEASE_3_20
    port: 8787
    tier: small
    enabled: true
    """
).strip()

JUPYTER = textwrap.dedent(
    """
    name: JupyterLab
    slug: jupyter
    image: quay.io/jupyter/datascience-notebook:latest
    port: 8888
    tier: small
    args:
      - start-notebook.py
    enabled: true
    """
).strip()


def test_load_valid_template():
    tmpl = load_template(RSTUDIO)
    assert tmpl.slug == "rstudio"
    assert tmpl.port == 8787
    assert tmpl.enabled is True
    # Defaults applied from the shared model.
    assert tmpl.resources.cpu == "1"


def test_camelcase_alias_accepted():
    tmpl = load_template("name: X\nslug: x\ndefaultDuration: 2h\n")
    assert tmpl.default_duration == "2h"


def test_valid_catalog():
    result = validate_documents({"rstudio.yaml": RSTUDIO, "jupyter.yaml": JUPYTER})
    assert result.ok
    assert {t.slug for t in result.templates} == {"rstudio", "jupyter"}


def test_empty_input_is_error():
    result = validate_documents({})
    assert not result.ok
    assert any("no template" in e for e in result.errors)


def test_duplicate_slug_rejected():
    result = validate_documents({"a.yaml": RSTUDIO, "b.yaml": RSTUDIO})
    assert not result.ok
    assert any("duplicate slug 'rstudio'" in e for e in result.errors)


def test_filename_must_match_slug():
    result = validate_documents({"wrong-name.yaml": RSTUDIO})
    assert not result.ok
    bad = result.files[0]
    assert not bad.ok
    assert any("does not match slug" in e for e in bad.errors)


def test_invalid_slug_reported_per_file():
    result = validate_documents({"Bad_Slug.yaml": "name: X\nslug: Bad_Slug\n"})
    assert not result.ok
    assert any("slug" in e for f in result.files for e in f.errors)


def test_invalid_yaml_reported():
    result = validate_documents({"broken.yaml": "name: X\n  bad: : :\n"})
    assert not result.ok
    assert any("invalid YAML" in e for f in result.files for e in f.errors)


def test_missing_required_field():
    result = validate_documents({"x.yaml": "slug: x\n"})  # no name
    assert not result.ok
    assert any("name" in e for f in result.files for e in f.errors)


def test_build_schema_shape():
    schema = build_schema()
    assert schema["title"] == "Orchestra Workshop Template"
    # camelCase aliases are used in the schema (by_alias=True)
    assert "defaultDuration" in schema["properties"]
    assert "slug" in schema["required"]


def test_cli_valid_dir(tmp_path, capsys):
    (tmp_path / "rstudio.yaml").write_text(RSTUDIO)
    (tmp_path / "jupyter.yaml").write_text(JUPYTER)
    rc = cli_main([str(tmp_path)])
    assert rc == 0
    assert "2 template file(s) valid" in capsys.readouterr().out


def test_cli_invalid_dir_returns_1(tmp_path):
    (tmp_path / "rstudio.yaml").write_text(RSTUDIO)
    (tmp_path / "dupe.yaml").write_text(RSTUDIO)  # duplicate slug
    assert cli_main([str(tmp_path)]) == 1


def test_cli_missing_dir_returns_2(tmp_path):
    assert cli_main([str(tmp_path / "nope")]) == 2


def test_cli_print_schema(capsys):
    assert cli_main(["--print-schema"]) == 0
    assert '"title": "Orchestra Workshop Template"' in capsys.readouterr().out


def test_cli_github_format_valid(tmp_path, capsys):
    (tmp_path / "rstudio.yaml").write_text(RSTUDIO)
    rc = cli_main([str(tmp_path), "--format", "github"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "::error" not in out
    assert "ok    rstudio.yaml" in out


def test_cli_github_format_emits_file_anchored_annotation(tmp_path, capsys):
    # Filename does not match slug -> per-file error anchored to that file.
    bad = tmp_path / "wrong-name.yaml"
    bad.write_text(RSTUDIO)
    rc = cli_main([str(tmp_path), "--format", "github"])
    out = capsys.readouterr().out
    assert rc == 1
    assert f"::error file={bad}," in out
    assert "does not match slug" in out


def test_cli_github_format_escapes_newlines(tmp_path, capsys):
    # An annotation message must be a single line; newlines are percent-encoded.
    (tmp_path / "broken.yaml").write_text("name: X\n  bad: : :\n")
    cli_main([str(tmp_path), "--format", "github"])
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("::error"):
            # message portion (after the last '::') carries no raw newline
            assert "\n" not in line
