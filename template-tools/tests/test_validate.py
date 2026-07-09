"""Tests for the shared template validation routine and CLI."""

import pathlib
import textwrap

import pytest
from pydantic import ValidationError

from orchestra_template_tools import (
    build_schema,
    load_template,
    validate_documents,
)
from orchestra_template_tools.cli import main as cli_main

_SHIPPED_TEMPLATES = (
    pathlib.Path(__file__).parents[2]
    / "deploy"
    / "charts"
    / "orchestra"
    / "files"
    / "templates"
)

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


def test_catalog_metadata_fields_accepted():
    tmpl = load_template(
        RSTUDIO
        + "\nurl: https://example.org/workshop"
        + "\nsourceUrl: https://github.com/org/repo"
        + "\nsubmittedBy: octocat"
    )
    assert str(tmpl.url) == "https://example.org/workshop"
    assert str(tmpl.source_url) == "https://github.com/org/repo"
    assert tmpl.submitted_by == "octocat"


def test_catalog_metadata_optional_absent_ok():
    tmpl = load_template(RSTUDIO)
    assert tmpl.url is None
    assert tmpl.source_url is None
    assert tmpl.submitted_by is None


def test_invalid_url_rejected():
    with pytest.raises(ValidationError):
        load_template(RSTUDIO + "\nurl: not-a-url")


def test_storage_size_at_cap_ok():
    # 20Gi is the cap itself; 21G (decimal) is under 20Gi (binary).
    for size in ("20Gi", "21G", "500Mi"):
        tmpl = load_template(RSTUDIO + f"\nstorage:\n  size: {size}")
        assert tmpl.storage.size == size


def test_storage_size_over_cap_rejected():
    for size in ("21Gi", "500Gi", "1Ti"):
        with pytest.raises(ValidationError, match="at most 20Gi"):
            load_template(RSTUDIO + f"\nstorage:\n  size: {size}")


def test_storage_size_malformed_rejected():
    for size in ("lots", "10GB", "-5Gi"):
        with pytest.raises(ValidationError, match="Kubernetes quantity"):
            load_template(RSTUDIO + f"\nstorage:\n  size: '{size}'")


def test_invalid_source_url_rejected():
    with pytest.raises(ValidationError):
        load_template(RSTUDIO + '\nsourceUrl: "ftp://example.org"')


def test_unknown_tag_rejected():
    with pytest.raises(ValidationError):
        load_template(RSTUDIO + "\ntags:\n  - not-a-real-tag")


def test_known_tags_accepted():
    tmpl = load_template(RSTUDIO + "\ntags:\n  - bioconductor\n  - rstudio")
    assert tmpl.tags == ["bioconductor", "rstudio"]


def test_shipped_templates_validate():
    files = {p.name: p.read_text() for p in _SHIPPED_TEMPLATES.glob("*.yaml")}
    assert files, "expected shipped template YAMLs to exist"
    result = validate_documents(files)
    assert result.ok, result.errors


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
