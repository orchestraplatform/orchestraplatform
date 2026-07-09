"""Issue-form body parsing (ADR-0009)."""

import pytest
import yaml

from orchestra_template_tools import (
    FormParseError,
    parse_args,
    parse_env,
    render_submission,
    submission_from_issue_body,
    validate_documents,
)

# A full form body as GitHub renders it (### label / value blocks, unchecked
# and checked checkboxes, _No response_ for empty optional fields).
FULL_BODY = """\
### Display name

RStudio (Bioconductor)

### Slug

rstudio

### Description

RStudio Server on the Bioconductor base image.

### Image

bioconductor/bioconductor_docker:RELEASE_3_20

### App port

8787

### Size

Large

### Tags

- [x] bioconductor
- [ ] jupyter
- [ ] python
- [x] rstudio

### Environment variables

DISABLE_AUTH=true
# a comment line
ROOT=true

### Container args

_No response_

### Storage size

20Gi

### Landing URL

https://example.org/workshop

### Source repo URL

_No response_
"""


def test_full_body_parses_to_submission():
    sub = submission_from_issue_body(FULL_BODY)
    assert sub == {
        "name": "RStudio (Bioconductor)",
        "slug": "rstudio",
        "description": "RStudio Server on the Bioconductor base image.",
        "image": "bioconductor/bioconductor_docker:RELEASE_3_20",
        "port": 8787,
        "size": "large",  # "Large" label -> preset key
        "tags": ["bioconductor", "rstudio"],
        "env": {"DISABLE_AUTH": "true", "ROOT": "true"},
        "storage": {"size": "20Gi"},
        "url": "https://example.org/workshop",
    }


def test_full_body_round_trips_to_valid_yaml():
    sub = submission_from_issue_body(FULL_BODY)
    result = render_submission(sub)
    assert result.ok, result.errors
    catalog = validate_documents({"rstudio.yaml": result.yaml_text})
    assert catalog.ok
    doc = yaml.safe_load(result.yaml_text)
    assert doc["tier"] == "large"  # size expanded
    assert doc["resources"]["memory"] == "8Gi"


def test_no_response_and_blank_fields_omitted():
    body = "### Display name\n\nX\n\n### Slug\n\nx\n\n### Description\n\n_No response_"
    assert submission_from_issue_body(body) == {"name": "X", "slug": "x"}


def test_xlarge_label_maps_to_xlarge_key():
    assert submission_from_issue_body("### Size\n\nX-Large")["size"] == "xlarge"


def test_size_label_resource_suffix_is_stripped():
    body = "### Size\n\nX-Large — 2 CPU, 16Gi memory, 8Gi ephemeral storage"
    assert submission_from_issue_body(body)["size"] == "xlarge"


def test_unknown_size_label_passes_through_verbatim():
    body = "### Size\n\nGigantic — 99 CPU"
    assert submission_from_issue_body(body)["size"] == "Gigantic — 99 CPU"


def test_no_tags_checked_omits_tags():
    body = "### Tags\n\n- [ ] bioconductor\n- [ ] jupyter"
    assert "tags" not in submission_from_issue_body(body)


def test_args_one_per_line():
    body = "### Container args\n\n--IdentityProvider.token=''\n--no-browser"
    assert submission_from_issue_body(body)["args"] == [
        "--IdentityProvider.token=''",
        "--no-browser",
    ]


def test_parse_env_value_may_contain_equals():
    assert parse_env("FOO=a=b=c") == {"FOO": "a=b=c"}


def test_parse_env_rejects_missing_equals():
    with pytest.raises(FormParseError, match="line 1: expected KEY=value"):
        parse_env("NOTANASSIGNMENT")


def test_parse_env_rejects_bad_key():
    with pytest.raises(FormParseError, match="invalid variable name"):
        parse_env("1BAD=x")


def test_parse_env_rejects_duplicate_key():
    with pytest.raises(FormParseError, match="duplicate"):
        parse_env("A=1\nA=2")


def test_parse_args_drops_blanks():
    assert parse_args("a\n\n  \nb") == ["a", "b"]


def test_markdown_heading_in_description_is_not_a_field_boundary():
    """A `### heading` inside the Markdown Description must stay in the
    description, not split the parse (regression: parser split on any ###)."""
    body = (
        "### Display name\n\nMy Workshop\n\n"
        "### Slug\n\nmy-workshop\n\n"
        "### Description\n\nIntro text.\n\n### Notes\n\nSome **markdown** notes.\n\n"
        "### Image\n\nrocker/rstudio:latest\n"
    )
    sub = submission_from_issue_body(body)
    assert sub["name"] == "My Workshop"
    assert sub["slug"] == "my-workshop"
    assert sub["image"] == "rocker/rstudio:latest"
    # The inner "### Notes" heading and its content stay inside the description.
    assert "### Notes" in sub["description"]
    assert "markdown** notes" in sub["description"]
