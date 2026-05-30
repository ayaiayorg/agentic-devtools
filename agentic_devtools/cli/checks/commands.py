"""CLI entry point for PR checks (agdt-pr-checks).

Single source of truth for both local pre-push hooks and CI targeted checks.
Both paths run identical validation — all checks execute in parallel for speed.

Usage:
    python -m agentic_devtools.cli.checks              # format --check (CI default)
    python -m agentic_devtools.cli.checks --format-fix # format auto-fix (pre-push hook)

Exit codes:
    0  — all checks passed
    N  — N check(s) failed (1-9)
    10 — ruff reformatted files (auto-fixable; pre-push hook can auto-amend)
"""

from __future__ import annotations

import os
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from agentic_devtools.cli.checks.changed_files import DiffUnavailableError, get_changed_files
from agentic_devtools.cli.checks.lint import (
    format_check_files,
    format_fix_files,
    lint_files,
    mypy_check_files,
)
from agentic_devtools.cli.checks.structure import validate_test_structure
from agentic_devtools.cli.checks.tests import _find_test_path, run_changed_tests, run_one_coverage


@dataclass
class _CheckResult:
    """Outcome of a single parallel check."""

    label: str
    passed: bool
    output: str
    duration: float = 0.0


# ---------------------------------------------------------------------------
# Check wrappers — each returns a _CheckResult with captured output
# ---------------------------------------------------------------------------


def _check_structure(cwd: Path) -> _CheckResult:
    t0 = time.monotonic()
    violations = validate_test_structure(cwd)
    dt = time.monotonic() - t0
    if violations:
        lines = [f"  - {v}" for v in violations]
        lines.append(f"FAIL: {len(violations)} violation(s)")
        return _CheckResult("Validate test structure", False, "\n".join(lines), dt)
    count = len(list((cwd / "tests" / "unit").rglob("test_*.py")))
    return _CheckResult(
        "Validate test structure",
        True,
        f"OK — {count} unit test file(s) validated, no violations found.",
        dt,
    )


def _check_lint(files: list[str], cwd: str) -> _CheckResult:
    t0 = time.monotonic()
    passed, output = lint_files(files, cwd=cwd)
    return _CheckResult("Lint changed files", passed, output, time.monotonic() - t0)


def _check_format(files: list[str], cwd: str) -> _CheckResult:
    t0 = time.monotonic()
    passed, output = format_check_files(files, cwd=cwd)
    return _CheckResult("ruff format --check", passed, output, time.monotonic() - t0)


def _check_mypy(files: list[str], cwd: str) -> _CheckResult:
    t0 = time.monotonic()
    passed, output = mypy_check_files(files, cwd=cwd)
    return _CheckResult("mypy type checking", passed, output, time.monotonic() - t0)


def _check_coverage(source_file: str, cwd: Path) -> _CheckResult:
    t0 = time.monotonic()
    passed, output = run_one_coverage(source_file, cwd=cwd)
    return _CheckResult(f"Coverage: {source_file}", passed, output, time.monotonic() - t0)


def _check_extra_tests(test_files: list[str], cwd: Path) -> _CheckResult:
    t0 = time.monotonic()
    passed, output = run_changed_tests(test_files, cwd=cwd)
    return _CheckResult("Additional changed tests", passed, output, time.monotonic() - t0)


def _max_workers() -> int:
    """Determine worker count: CPU count capped at 8."""
    return min(os.cpu_count() or 4, 8)


# ---------------------------------------------------------------------------
# Output condensing — strip verbose pytest/coverage noise from failure output
# ---------------------------------------------------------------------------

# Sections of pytest output that are noise for diagnosing failures.
_SKIP_PREFIXES = (
    "platform ",
    "cachedir: ",
    "rootdir: ",
    "configfile: ",
    "plugins: ",
    "collecting ",
    "collected ",
)


def _condense_output(raw: str) -> str:
    """Condense verbose check output by stripping common noise.

    Currently this helper:
    - Removes individual per-test "... PASSED" lines (with "::")
    - Removes common pytest metadata lines (platform/cachedir/rootdir/config/plugins/collecting/collected)
    - Collapses consecutive blank lines and trims trailing blanks

    It does not attempt to keep *only* failing/error lines; any other non-noise
    lines are preserved.
    """
    lines = raw.splitlines()
    kept: list[str] = []
    prev_blank = False

    for line in lines:
        stripped = line.strip()

        # Always keep blank lines (but collapse runs of blanks)
        if not stripped:
            if not prev_blank:
                kept.append("")
                prev_blank = True
            continue
        prev_blank = False

        # Skip individual PASSED test lines (e.g., "tests/unit/.../test_foo.py::TestX::test_y PASSED")
        if stripped.endswith(" PASSED") and "::" in stripped:
            continue

        # Skip pytest metadata noise
        if any(stripped.startswith(p) for p in _SKIP_PREFIXES):
            continue

        kept.append(line)

    # Remove trailing blank lines
    while kept and not kept[-1].strip():
        kept.pop()

    return "\n".join(kept)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def _run_checks(cwd: Path, *, format_fix: bool = False) -> int:
    """Run all targeted checks, parallelising where possible.

    Format auto-fix (``--format-fix``) runs first since it modifies files;
    all other checks run concurrently in a thread pool.

    Returns the number of failures (0 = all passed).
    """
    # Force UTF-8 stdout so box-drawing characters survive on Windows cp1252 terminals.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    wall_t0 = time.monotonic()

    print("========================================")
    print("  Targeted Checks")
    print("========================================")

    # ── Gather changed files ──────────────────────────────────────────────
    try:
        changed_py = get_changed_files(cwd=cwd)
    except DiffUnavailableError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Cannot safely run targeted checks without changed-file detection.", file=sys.stderr)
        return 1
    try:
        changed_source = get_changed_files(source_only=True, cwd=cwd)
    except DiffUnavailableError:
        changed_source = []
    try:
        changed_tests = get_changed_files(tests_only=True, cwd=cwd)
    except DiffUnavailableError:
        changed_tests = []

    print(f"Changed Python files: {len(changed_py)} ({len(changed_source)} source, {len(changed_tests)} test)")

    # ── Format auto-fix (must complete before parallel phase) ─────────────
    if format_fix:
        print("\n── ruff format (auto-fix) ──")
        if changed_py:
            passed, output = format_fix_files(changed_py, cwd=str(cwd))
            print(output)
            if not passed:
                if output.startswith("ERROR:"):
                    print("\n❌ ruff format failed.")
                    return 1
                print("\n❌ Files were reformatted by ruff. Stage and amend, then push again.")
                return 10  # Distinct exit code: auto-fixable reformatting
        else:
            print("No Python files changed, skipping format.")

    # ── Build and submit parallel checks ──────────────────────────────────
    futures: list[Future[_CheckResult]] = []

    with ThreadPoolExecutor(max_workers=_max_workers()) as pool:
        futures.append(pool.submit(_check_structure, cwd))

        if changed_py:
            futures.append(pool.submit(_check_lint, changed_py, str(cwd)))
            if not format_fix:
                futures.append(pool.submit(_check_format, changed_py, str(cwd)))
            futures.append(pool.submit(_check_mypy, changed_py, str(cwd)))

        for src in changed_source:
            futures.append(pool.submit(_check_coverage, src, cwd))

        # Additional changed test files not already covered by per-file coverage
        covered_dirs: set[Path] = set()
        covered_files: set[Path] = set()
        for src in changed_source:
            tp = _find_test_path(src, cwd)
            if tp:
                test_path = Path(tp)
                if not test_path.is_absolute():
                    test_path = cwd / test_path
                test_path = test_path.resolve(strict=False)
                if test_path.suffix == ".py":
                    covered_files.add(test_path)
                else:
                    covered_dirs.add(test_path)

        remaining: list[str] = []
        for test_file in changed_tests:
            candidate = (cwd / test_file).resolve(strict=False)
            if candidate in covered_files:
                continue
            if any(covered_dir in candidate.parents for covered_dir in covered_dirs):
                continue
            remaining.append(test_file)
        if remaining:
            futures.append(pool.submit(_check_extra_tests, remaining, cwd))

        # ── Progress counter ──────────────────────────────────────────────
        total = len(futures)
        print(f"\nRunning {total} check(s) in parallel...\n")
        completed = 0
        for _ in as_completed(futures):
            completed += 1
            print(f"  Progress: {completed}/{total}")

    # ── Print results in submission order ─────────────────────────────────
    results: list[_CheckResult] = []
    for fut in futures:
        try:
            results.append(fut.result())
        except Exception as exc:  # noqa: BLE001
            msg = f"Unexpected exception: {exc!r}"
            results.append(_CheckResult(label="(unexpected error)", passed=False, output=msg))
    failures = 0
    failed_details: list[_CheckResult] = []

    print()
    for r in results:
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {r.label} ({r.duration:.1f}s)")
        if not r.passed:
            failures += 1
            failed_details.append(r)

    # ── Detailed output for failures ──────────────────────────────────────
    if failed_details:
        # Save full verbose output to file for reference
        full_log_path = cwd / "check-output.txt"
        with open(full_log_path, "w", encoding="utf-8") as fh:
            for r in results:
                icon = "✓" if r.passed else "✗"
                fh.write(f"{icon} {r.label} ({r.duration:.1f}s)\n")
                if r.output.strip():
                    fh.write(r.output)
                    fh.write("\n\n")
        print(f"\n  Full output saved to: {full_log_path}")

        # Build condensed output for terminal and file
        condensed_lines: list[str] = []
        condensed_lines.append(f"{'─' * 60}")
        condensed_lines.append(f"  Detail for {failures} failed check(s):")
        condensed_lines.append(f"{'─' * 60}")
        for r in failed_details:
            condensed_lines.append(f"\n┌── {r.label} ──")
            for line in _condense_output(r.output).splitlines():
                condensed_lines.append(f"│ {line}")
            condensed_lines.append("└" + "─" * 40)
        condensed_text = "\n".join(condensed_lines)

        # Save condensed output to file
        condensed_log_path = cwd / "check-output-condensed.txt"
        with open(condensed_log_path, "w", encoding="utf-8") as fh:
            fh.write(condensed_text)
            fh.write("\n")
        print(f"  Condensed output saved to: {condensed_log_path}")

        # Show condensed output in terminal
        print(f"\n{condensed_text}")

    # ── Summary ───────────────────────────────────────────────────────────
    wall_dt = time.monotonic() - wall_t0
    print("\n========================================")
    if failures == 0:
        print(f"  All targeted checks passed! ({wall_dt:.1f}s)")
    else:
        print(f"  {failures} check(s) failed ({wall_dt:.1f}s)")
    print("========================================")

    # Exit code 10 is reserved for the "ruff reformatted files" signal.
    # Clamp non-format failure counts to 1–9 to avoid ambiguity.
    return 0 if failures == 0 else min(failures, 9)


def main() -> int:
    """Entry point for ``python -m agentic_devtools.cli.checks``."""
    cwd = Path.cwd()
    format_fix = "--format-fix" in sys.argv
    return _run_checks(cwd, format_fix=format_fix)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
