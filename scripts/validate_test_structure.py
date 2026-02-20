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
UNIT_TESTS_DIR = REPO_ROOT / "tests" / "unit"
SOURCE_ROOT = REPO_ROOT / "agentic_devtools"


def validate() -> list[str]:
    """Return a list of violation messages (empty list means no violations)."""
    violations: list[str] = []

    if not UNIT_TESTS_DIR.exists():
        # No unit tests yet — nothing to validate.
        return violations

    for test_file in sorted(UNIT_TESTS_DIR.rglob("test_*.py")):
        rel = test_file.relative_to(UNIT_TESTS_DIR)
        parts = rel.parts  # e.g. ("cli", "git", "core", "test_get_current_branch.py")

        # Rule: test file must be exactly one level inside a source-file folder.
        # Minimum depth: source_file_name folder + test file = >= 2 parts.
        # Root-level source files (e.g. agentic_devtools/background_tasks.py) have 2 parts;
        # deeper modules (e.g. agentic_devtools/cli/testing.py) have 3+ parts.
        if len(parts) < 2:
            violations.append(
                f"{rel}: test file is too shallow — expected "
                f"tests/unit/{{source_file}}/test_{{function}}.py "
                f"(minimum 2 path components, got {len(parts)})"
            )
            continue

        # The immediate parent directory is the source-file name (without .py).
        source_file_folder = parts[-2]
        # The grandparent and above form the module path inside agentic_devtools/.
        module_path_parts = parts[:-2]

        # Rule: the corresponding source file must exist.
        expected_source = SOURCE_ROOT.joinpath(*module_path_parts) / f"{source_file_folder}.py"
        if not expected_source.exists():
            source_path_display = "/".join((*module_path_parts, f"{source_file_folder}.py"))
            violations.append(
                f"{rel}: no matching source file found at "
                f"agentic_devtools/{source_path_display}"
            )

        # Rule: every intermediate directory must have an __init__.py.
        current = UNIT_TESTS_DIR
        for part in parts[:-1]:  # walk all ancestor dirs of the test file
            current = current / part
            init = current / "__init__.py"
            if not init.exists():
                violations.append(f"{rel}: missing __init__.py in {current.relative_to(REPO_ROOT)}")

    return violations


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
