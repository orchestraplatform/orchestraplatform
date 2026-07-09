"""Parse a GitHub issue-form body into a template submission dict (ADR-0009).

GitHub renders a submitted issue form as a markdown body of ``### <label>``
headings each followed by the field's value; empty optional fields render as
``_No response_``. This module turns that body back into the submission dict
:func:`orchestra_template_tools.render.render_submission` expects — shared by
the front-door Actions and the local ``just template-from-issue`` fallback so
they can't drift.

The ``env``/``args`` textarea parsing is the Python port of
``frontend/src/utils/envArgs.ts``.
"""

import re

# POSIX-ish env var name: letter/underscore, then alphanumerics/underscore.
_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)
_CHECKED_RE = re.compile(r"^- \[[xX]\]\s+(.+?)\s*$")
_NO_RESPONSE = "_No response_"

# Size dropdown option labels -> preset keys (see presets.SIZE_PRESETS).
# The form labels carry a resource suffix ("Small — 2 CPU, ..."); the name
# before the em-dash is what maps here (stripped in submission_from_issue_body).
_SIZE_LABELS = {
    "small": "small",
    "standard": "standard",
    "large": "large",
    "x-large": "xlarge",
    "xlarge": "xlarge",
}


class FormParseError(ValueError):
    """A form field couldn't be parsed (e.g. a malformed ``env`` line).

    Message is a field-level ``loc: detail`` string, ready to post verbatim as
    an issue comment alongside the model's own validation errors.
    """


def parse_env(text: str) -> dict[str, str]:
    """Parse dotenv-style ``KEY=value`` lines into a dict.

    Blank lines and ``#`` comments are ignored; the value is everything after
    the first ``=``. Raises :class:`FormParseError` on a missing ``=``, an
    invalid key, or a duplicate key.
    """
    env: dict[str, str] = {}
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if line == "" or line.startswith("#"):
            continue
        if "=" not in line:
            raise FormParseError(f"env: line {i}: expected KEY=value")
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if not _ENV_KEY_RE.match(key):
            raise FormParseError(f"env: line {i}: invalid variable name {key!r}")
        if key in env:
            raise FormParseError(f"env: line {i}: duplicate variable {key!r}")
        env[key] = val
    return env


def parse_args(text: str) -> list[str]:
    """One argument per line; blank lines dropped."""
    return [line.strip() for line in text.splitlines() if line.strip() != ""]


def _parse_tags(text: str) -> list[str]:
    """Checked checkbox lines (``- [x] value``) -> the checked values."""
    return [
        m.group(1)
        for line in text.splitlines()
        if (m := _CHECKED_RE.match(line.strip()))
    ]


# The workshop-template form's field labels — the ONLY headings that delimit a
# field. Any other ``### ...`` line (e.g. a heading inside a Markdown Description)
# is kept as content, not treated as a field boundary.
_FIELD_LABELS = frozenset(
    {
        "Display name",
        "Slug",
        "Description",
        "Image",
        "App port",
        "Size",
        "Tags",
        "Environment variables",
        "Container args",
        "Storage size",
        "Landing URL",
        "Source repo URL",
    }
)


def parse_issue_body(body: str) -> dict[str, str]:
    """Split an issue-form markdown body into ``{field label: raw value}``.

    Only the known form-field labels (:data:`_FIELD_LABELS`) delimit fields, so a
    ``### heading`` an instructor writes inside a value (the Description supports
    Markdown) is preserved as content rather than corrupting the parse.
    """
    blocks: dict[str, str] = {}
    matches = [
        m for m in _HEADING_RE.finditer(body) if m.group(1).strip() in _FIELD_LABELS
    ]
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        blocks[m.group(1).strip()] = body[start:end].strip()
    return blocks


def submission_from_issue_body(body: str) -> dict[str, object]:
    """Turn a workshop-template issue-form body into a submission dict.

    Keys are the form field labels (see
    ``.github/ISSUE_TEMPLATE/workshop-template.yml``). Empty/``_No response_``
    fields are omitted so model defaults apply; ``size`` is left for
    ``render_submission`` to expand. Raises :class:`FormParseError` on a
    malformed ``env`` block.
    """
    blocks = parse_issue_body(body)

    def field(label: str) -> str | None:
        v = blocks.get(label, "").strip()
        return None if v in ("", _NO_RESPONSE) else v

    out: dict[str, object] = {}
    if (v := field("Display name")) is not None:
        out["name"] = v
    if (v := field("Slug")) is not None:
        out["slug"] = v
    if (v := field("Description")) is not None:
        out["description"] = v
    if (v := field("Image")) is not None:
        out["image"] = v
    if (v := field("App port")) is not None:
        # Let pydantic report a non-numeric port; only coerce clean integers.
        out["port"] = int(v) if v.lstrip("-").isdigit() else v
    if (v := field("Size")) is not None:
        # Drop the label's resource suffix ("Small — 2 CPU, ..." -> "Small").
        # Unknown label passes through so render_submission emits "unknown size".
        name = v.split("—", 1)[0].strip()
        out["size"] = _SIZE_LABELS.get(name.lower(), v)
    if tags := _parse_tags(blocks.get("Tags", "")):
        out["tags"] = tags
    if (v := field("Environment variables")) is not None:
        out["env"] = parse_env(v)
    if (v := field("Container args")) is not None:
        out["args"] = parse_args(v)
    if (v := field("Storage size")) is not None:
        out["storage"] = {"size": v}
    if (v := field("Landing URL")) is not None:
        out["url"] = v
    if (v := field("Source repo URL")) is not None:
        out["sourceUrl"] = v
    return out
