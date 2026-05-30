#!/usr/bin/env python3
"""
Check that every changed agentic_devtools/*.py file has passing tests
with 100% coverage. Used by CI pipelines and the pre-push hook for
thorough validation.

Delegates to agentic_devtools.cli.checks for the actual logic.

Usage:
    python3 scripts/check-pr-test-coverage.py                  # diff against origin/main
    python3 scripts/check-pr-test-coverage.py main              # diff against local main
    python3 scripts/check-pr-test-coverage.py HEAD~1            # diff against previous commit

Exit code 0 = all checks pass, non-zero = failures.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Ensure the repo root is on sys.path so agentic_devtools can be imported
# when this script is run directly (python3 scripts/check-pr-test-coverage.py).
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    """Delegate to the checks module for per-file coverage."""
    from agentic_devtools.cli.checks.changed_files import DiffUnavailableError, get_changed_files
    from agentic_devtools.cli.checks.tests import run_coverage_check

    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    workspace = Path.cwd()

    print("=" * 50)
    print(f"PR Test Coverage Check (vs {base_ref})")
    print("=" * 50)

    try:
        changed = get_changed_files(base_ref, source_only=True, cwd=workspace)
    except DiffUnavailableError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    if not changed:
        print("\nNo changed agentic_devtools/*.py source files found.")
        print("PASS: Nothing to check.")
        return 0

    print(f"\nChanged source files ({len(changed)}):")
    for f in changed:
        print(f"  {f}")
    print()

    total, failures = run_coverage_check(changed, cwd=workspace)

    print()
    print("=" * 50)
    if failures == 0:
        print(f"PASS: All {total} file(s) pass with 100% coverage!")
        return 0
    else:
        print(f"FAIL: {failures} of {total} file(s) failed coverage check")
        return 1


if __name__ == "__main__":
    sys.exit(main())
