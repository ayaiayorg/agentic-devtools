"""Test execution for changed files and coverage checks.

All functions capture subprocess output and return ``(passed, output)``
tuples so they can be called from a thread pool without interleaving stdout.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_changed_tests(
    test_files: list[str],
    *,
    cwd: str | Path | None = None,
) -> tuple[bool, str]:
    """Run pytest on specific test files (no coverage). Returns (passed, output)."""
    if not test_files:
        return True, ""
    cwd_str = str(cwd) if cwd else None
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *test_files,
            "--no-cov",
            "-q",
            "-o",
            "addopts=",
            "-W",
            "ignore::DeprecationWarning",
            "-W",
            "ignore::PendingDeprecationWarning",
        ],
        capture_output=True,
        text=True,
        cwd=cwd_str,
    )
    return result.returncode == 0, (result.stdout + result.stderr).rstrip()


def _find_test_path(source_file: str, workspace: Path) -> str | None:
    """Find the test path for a source file (1:1:1 or legacy layout)."""
    relative = source_file.removeprefix("agentic_devtools/")
    relative_dir = relative.removesuffix(".py")
    unit_test_dir = workspace / "tests" / "unit" / relative_dir
    if unit_test_dir.is_dir():
        return str(unit_test_dir)

    basename = Path(source_file).stem
    legacy_test_file = workspace / "tests" / f"test_{basename}.py"
    if legacy_test_file.is_file():
        return str(legacy_test_file)

    return None


def run_one_coverage(
    source_file: str,
    *,
    cwd: str | Path | None = None,
) -> tuple[bool, str]:
    """Run 100% branch coverage check for a single source file.

    Returns ``(passed, output)``.
    """
    workspace = Path(cwd) if cwd else Path.cwd()
    source_module = source_file.replace("/", ".").replace("\\", ".").removesuffix(".py")
    test_path = _find_test_path(source_file, workspace)

    if test_path is None:
        return False, f"FAIL: No tests found for {source_file}"

    header = f"-- {source_file} -> {test_path} --"

    # Isolate coverage data file per subprocess to avoid PermissionError
    # when multiple pytest-cov processes run in parallel on Windows.
    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="cov_") as cov_dir:
        env["COVERAGE_FILE"] = str(Path(cov_dir) / ".coverage")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                test_path,
                "-v",
                "--tb=short",
                "-o",
                "addopts=",
                "-W",
                "ignore::DeprecationWarning",
                "-W",
                "ignore::PendingDeprecationWarning",
                f"--cov={source_module}",
                "--cov-branch",
                "--cov-report=term-missing",
                "--cov-fail-under=100",
            ],
            capture_output=True,
            text=True,
            cwd=str(workspace),
            env=env,
        )
    lines = [header, result.stdout.rstrip()]
    if result.stderr.strip():
        lines.append(result.stderr.rstrip())
    if result.returncode != 0:
        lines.append(f"FAIL: {source_file} — tests failing or < 100% coverage")
    return result.returncode == 0, "\n".join(lines)


def run_coverage_check(
    source_files: list[str],
    *,
    cwd: str | Path | None = None,
) -> tuple[int, int]:
    """Run per-file 100% branch coverage (sequential). Returns (total, failures).

    Prefer :func:`run_one_coverage` with a thread pool for parallel execution.
    """
    failures = 0
    total = len(source_files)

    for source_file in source_files:
        passed, output = run_one_coverage(source_file, cwd=cwd)
        print(output)
        if not passed:
            failures += 1

    return total, failures
