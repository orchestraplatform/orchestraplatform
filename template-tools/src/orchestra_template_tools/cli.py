"""Console entry points for the package.

``orchestra-validate-templates`` — validate a local directory of template
files. Used by the platform's ``just validate-templates`` and by the
workshop-templates repo's CI. Reads ``*.yaml`` / ``*.yml`` from a directory
and validates them with the shared :func:`validate_documents` routine. Exits
non-zero on any error.

``orchestra-render-template`` — render a template submission (parsed
issue-form fields as JSON) to canonical template YAML (ADR-0009). Emits a
JSON result envelope for the front-door Action to consume.
"""

import argparse
import json
import sys
from pathlib import Path

from .render import RenderResult, existing_template_path, render_submission
from .schema import schema_json
from .validate import validate_documents


def _read_dir(directory: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")]):
        docs[path.name] = path.read_text()
    return docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orchestra-validate-templates",
        description="Validate Orchestra workshop-template YAML files.",
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory containing template *.yaml files (default: current dir)",
    )
    parser.add_argument(
        "--print-schema",
        action="store_true",
        help="Print the template JSON Schema to stdout and exit.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "github"),
        default="text",
        help=(
            "Output format. 'text' (default) is human-readable; 'github' emits "
            "GitHub Actions annotations (::error file=...) so each failing "
            "document is flagged inline on the pull request."
        ),
    )
    args = parser.parse_args(argv)

    if args.print_schema:
        sys.stdout.write(schema_json())
        return 0

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"error: {directory} is not a directory", file=sys.stderr)
        return 2

    result = validate_documents(_read_dir(directory))

    if args.format == "github":
        return _report_github(result, directory)
    return _report_text(result, directory)


def _report_text(result, directory: Path) -> int:
    for f in result.files:
        if f.ok:
            print(f"  ok    {f.name}")
        else:
            print(f"  FAIL  {f.name}")
            for err in f.errors:
                print(f"          - {err}")
    for err in result.errors:
        print(f"  FAIL  <catalog>: {err}")

    n = len(result.files)
    if result.ok:
        print(f"\n✓ {n} template file(s) valid in {directory}")
        return 0
    print(f"\n✗ validation failed in {directory}", file=sys.stderr)
    return 1


def _gh_escape(message: str) -> str:
    """Escape a message for a GitHub Actions workflow command (single line)."""
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _report_github(result, directory: Path) -> int:
    """Emit GitHub Actions ``::error file=...`` annotations, one per problem.

    ``file=`` is anchored to the actual template path so the annotation renders
    inline on the changed file in the PR. Catalog-level errors anchor to the
    directory. Exit code matches the text formatter.
    """
    for f in result.files:
        path = directory / f.name
        if f.ok:
            print(f"  ok    {f.name}")
            continue
        for err in f.errors:
            print(
                f"::error file={path},title=Invalid workshop template::"
                f"{_gh_escape(f'{f.name}: {err}')}"
            )

    for err in result.errors:
        print(
            f"::error file={directory},title=Template catalog error::{_gh_escape(err)}"
        )

    n = len(result.files)
    if result.ok:
        print(f"✓ {n} template file(s) valid in {directory}")
        return 0
    print(f"✗ validation failed in {directory}", file=sys.stderr)
    return 1


def render_main(argv: list[str] | None = None) -> int:
    """``orchestra-render-template`` — submission JSON in, result JSON out.

    Prints a JSON envelope to stdout: ``ok``, ``errors`` (field-level, ready
    for an issue comment), ``slug``, ``yaml``, and — when ``--templates-dir``
    is given — ``exists`` plus the ``path`` to write (existing file for an
    update, ``<slug>.yaml`` in the directory for a create). Exit 0 iff valid.
    """
    parser = argparse.ArgumentParser(
        prog="orchestra-render-template",
        description="Render a template submission (JSON) as canonical template YAML.",
    )
    parser.add_argument(
        "submission",
        nargs="?",
        default="-",
        help="Path to the submission JSON file ('-' or omitted: read stdin)",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=None,
        help="Templates directory to resolve create-vs-update against.",
    )
    args = parser.parse_args(argv)

    if args.submission == "-":
        raw = sys.stdin.read()
    else:
        path = Path(args.submission)
        if not path.is_file():
            # Same JSON envelope as every other exit path — consumers parse
            # stdout unconditionally.
            result = RenderResult(ok=False, errors=[f"{path}: not a file"])
            print(_envelope(result, None))
            return 2
        raw = path.read_text()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        result = RenderResult(ok=False, errors=[f"<root>: invalid JSON: {exc}"])
    else:
        result = render_submission(data)

    print(_envelope(result, args.templates_dir))
    return 0 if result.ok else 1


def _envelope(result: RenderResult, templates_dir: Path | None) -> str:
    """The JSON result envelope every render_main exit path emits."""
    out: dict = {
        "ok": result.ok,
        "errors": result.errors,
        "slug": result.template.slug if result.template else None,
        "yaml": result.yaml_text,
        "exists": None,
        "path": None,
    }
    if result.ok and templates_dir is not None:
        existing = existing_template_path(result.template.slug, templates_dir)
        out["exists"] = existing is not None
        target = existing or templates_dir / f"{result.template.slug}.yaml"
        out["path"] = str(target)
    return json.dumps(out, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
