"""``orchestra-validate-templates`` — validate a local directory of template files.

Used by the platform's ``just validate-templates`` and by the workshop-templates
repo's CI. Reads ``*.yaml`` / ``*.yml`` from a directory and validates them with
the shared :func:`validate_documents` routine. Exits non-zero on any error.
"""

import argparse
import sys
from pathlib import Path

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
    args = parser.parse_args(argv)

    if args.print_schema:
        sys.stdout.write(schema_json())
        return 0

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"error: {directory} is not a directory", file=sys.stderr)
        return 2

    result = validate_documents(_read_dir(directory))

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


if __name__ == "__main__":
    raise SystemExit(main())
