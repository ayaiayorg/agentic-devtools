#!/usr/bin/env python3
"""Validate the 1:1:1 test structure policy for tests/unit/.

Policy (see tests/README.md):
  - One folder per source file under test (mirrors agentic_devtools/ structure).
  - One test file per function under test.
  - Test files must be named test_{function_name}.py.
  - Every directory must contain an __init__.py file.

Expected layout:
  tests/unit/{module_path}/{source_file_name}/test_{function_name}.py

This script exits with status 0 when all rules are satisfied, or 1 when any
violation is found.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Ensure the repo root is on sys.path so agentic_devtools can be imported
# when this script is run directly (python scripts/validate_test_structure.py).
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
UNIT_TESTS_DIR = REPO_ROOT / "tests" / "unit"
SOURCE_ROOT = REPO_ROOT / "agentic_devtools"


def validate() -> list[str]:
    """Return a list of violation messages (empty list means no violations)."""
    from agentic_devtools.cli.checks.structure import validate_test_structure as _validate

    return _validate(REPO_ROOT)


def main() -> int:
    violations = validate()

    if not violations:
        unit_files = list(UNIT_TESTS_DIR.rglob("test_*.py")) if UNIT_TESTS_DIR.exists() else []
        print(f"OK — {len(unit_files)} unit test file(s) validated, no violations found.")
        return 0

    print(f"FAIL — {len(violations)} violation(s) found in tests/unit/:\n")
    for v in violations:
        print(f"  - {v}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
