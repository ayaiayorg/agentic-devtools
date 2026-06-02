"""Ruff lint, format, and mypy type checks.

All functions capture subprocess output and return ``(passed, output)``
so they can be called from a thread pool without interleaving stdout.
"""

from __future__ import annotations

import subprocess


def lint_files(files: list[str], *, cwd: str | None = None) -> tuple[bool, str]:
    """Run ruff check on the given files. Returns (passed, output)."""
    if not files:
        return True, ""
    result = subprocess.run(
        ["ruff", "check"] + files,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).rstrip()


def format_fix_files(files: list[str], *, cwd: str | None = None) -> tuple[bool, str]:
    """Run ruff format (auto-fix) on the given files.

    Returns ``(no_changes_made, format_output)``.
    *True* means all files were already formatted (no changes).
    *False* means files were reformatted (caller should abort push).
    """
    if not files:
        return True, ""
    proc = subprocess.run(
        ["ruff", "format"] + files,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout + proc.stderr).rstrip()
    if proc.returncode != 0:
        return False, f"ERROR: ruff format failed\n{output}".rstrip()

    # Check if any files were modified by the format
    diff = subprocess.run(
        ["git", "diff", "--name-only", "--"] + files,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if diff.stdout.strip():
        return False, output
    return True, output


def format_check_files(files: list[str], *, cwd: str | None = None) -> tuple[bool, str]:
    """Run ruff format --check on the given files. Returns (passed, output)."""
    if not files:
        return True, ""
    result = subprocess.run(
        ["ruff", "format", "--check"] + files,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).rstrip()


def mypy_check_files(files: list[str], *, cwd: str | None = None) -> tuple[bool, str]:
    """Run mypy on the given files. Returns (passed, output)."""
    if not files:
        return True, ""
    result = subprocess.run(
        ["mypy", "--ignore-missing-imports", "--follow-imports=silent"] + files,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, (result.stdout + result.stderr).rstrip()
