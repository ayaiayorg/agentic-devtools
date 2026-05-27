#!/usr/bin/env python3
"""
Check that every changed agentic_devtools/*.py file has passing tests
with 100% coverage. Intended for humans and CI pipelines.
AI agents should use agdt-test / agdt-test-file commands instead.

Excludes __init__.py and _version.py (auto-generated / no testable logic).

Usage:
    python3 scripts/check-pr-test-coverage.py                  # diff against origin/main
    python3 scripts/check-pr-test-coverage.py main              # diff against local main
    python3 scripts/check-pr-test-coverage.py HEAD~1            # diff against previous commit

Exit code 0 = all checks pass, non-zero = failures.
"""

import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
EXCLUDE_PATTERNS = {"__pycache__", "_version.py", "__init__.py"}


def _run(args: list[str], cwd: str) -> int:
    """Run a command, streaming output, and return exit code."""
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    if process.stdout:
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
    process.wait()
    return process.returncode


def _get_changed_files(base_ref: str, cwd: str) -> list[str]:
    """Get list of changed agentic_devtools/*.py files between base_ref and HEAD.

    Uses --diff-filter=d to exclude deleted files so we don't attempt
    coverage runs against modules that no longer exist.
    """
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=d",
            f"{base_ref}..HEAD",
            "--",
            "agentic_devtools/*.py",
            "agentic_devtools/**/*.py",
        ],
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != 0:
        print(f"ERROR: git diff failed (exit code {result.returncode})")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()}")
        sys.exit(1)
    files = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if any(pat in line for pat in EXCLUDE_PATTERNS):
            continue
        files.append(line)
    return files


def _find_test_path(source_file: str, workspace: str) -> str | None:
    """Find the test path for a source file (1:1:1 or legacy layout)."""
    # 1:1:1: agentic_devtools/cli/git/core.py → tests/unit/cli/git/core/
    relative = source_file.removeprefix("agentic_devtools/")
    relative_dir = relative.removesuffix(".py")
    unit_test_dir = Path(workspace) / "tests" / "unit" / relative_dir
    if unit_test_dir.is_dir():
        return str(unit_test_dir)

    # Legacy: agentic_devtools/cli/git/core.py → tests/test_core.py
    basename = Path(source_file).stem
    legacy_test_file = Path(workspace) / "tests" / f"test_{basename}.py"
    if legacy_test_file.is_file():
        return str(legacy_test_file)

    return None


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    workspace = str(Path.cwd())

    print("=" * 50)
    print(f"PR Test Coverage Check (vs {base_ref})")
    print("=" * 50)

    # Step 1: Collect changed source files
    changed = _get_changed_files(base_ref, workspace)
    if not changed:
        print("\nNo changed agentic_devtools/*.py source files found.")
        print("PASS: Nothing to check.")
        return 0

    print(f"\nChanged source files ({len(changed)}):")
    for f in changed:
        print(f"  {f}")
    print()

    # Step 2: Full test suite (all tests must pass)
    print("-- Step 1/2: Full test suite (all tests must pass) --")
    rc = _run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "-o", "addopts=", "--no-cov"],
        cwd=workspace,
    )
    if rc != 0:
        print("\nFAIL: Some tests are failing. Fix all test failures first.")
        return 1

    # Step 3: Per-file coverage
    print()
    print("-- Step 2/2: Per-file 100% branch coverage --")

    failures = 0
    checked = 0
    total_files = len(changed)

    for source_file in changed:
        # Convert path to module: agentic_devtools/cli/git/core.py → agentic_devtools.cli.git.core
        source_module = source_file.replace("/", ".").replace("\\", ".").removesuffix(".py")
        test_path = _find_test_path(source_file, workspace)

        if test_path is None:
            print(f"\nFAIL: No tests found for {source_file}")
            failures += 1
            continue

        checked += 1
        print(f"\n-- [{checked}] {source_file} -> {test_path} --")

        rc = _run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "-o",
                "addopts=",
                f"--cov={source_module}",
                "--cov-branch",
                "--cov-report=term-missing",
                "--cov-fail-under=100",
            ],
            cwd=workspace,
        )
        if rc != 0:
            print(f"FAIL: {source_file} — tests failing or < 100% coverage")
            failures += 1

    # Summary
    print()
    print("=" * 50)
    if failures == 0:
        print(f"PASS: All {total_files} file(s) pass with 100% coverage!")
        return 0
    else:
        print(f"FAIL: {failures} of {total_files} file(s) failed coverage check")
        return 1


if __name__ == "__main__":
    sys.exit(main())
