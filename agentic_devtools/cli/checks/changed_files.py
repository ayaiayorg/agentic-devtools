"""Git diff helpers for identifying changed files."""

from __future__ import annotations

import subprocess
from pathlib import Path

EXCLUDE_PATTERNS = {"__pycache__", "_version.py"}
COVERAGE_EXCLUDE_PATTERNS = {"__init__.py", "__main__.py"}


class DiffUnavailableError(RuntimeError):
    """Raised when git diff cannot determine changed files."""


def get_changed_files(
    base_ref: str = "origin/main",
    *,
    pattern: str = "*.py",
    source_only: bool = False,
    tests_only: bool = False,
    cwd: str | Path | None = None,
) -> list[str]:
    """Return changed files between base_ref and HEAD.

    Uses merge-base diff (``...``) for accurate results. If the primary
    diff fails (e.g. ``origin/main`` not available), tries local fallbacks
    suitable for shallow repositories. Raises :class:`DiffUnavailableError`
    when all strategies fail.

    Args:
        base_ref: Git ref to diff against.
        pattern: Glob pattern for git diff (e.g. '*.py').
        source_only: Only return files under agentic_devtools/.
        tests_only: Only return files under tests/.
        cwd: Working directory for git commands.

    Returns:
        List of relative file paths.

    Raises:
        DiffUnavailableError: When both diff strategies fail.
    """
    cwd_str = str(cwd) if cwd else None
    pathspecs = []
    if source_only:
        pathspecs = ["agentic_devtools/*.py", "agentic_devtools/**/*.py"]
    elif tests_only:
        pathspecs = ["tests/**/*.py"]
    else:
        if "/" not in pattern and "\\" not in pattern:
            pathspecs = [pattern, f"**/{pattern}"]
        else:
            pathspecs = [pattern]

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=d", f"{base_ref}...HEAD", "--"] + pathspecs,
            capture_output=True,
            text=True,
            cwd=cwd_str,
        )
    except (FileNotFoundError, OSError) as exc:
        raise DiffUnavailableError(f"git diff unavailable (could not execute git): {exc}") from exc
    if result.returncode != 0:
        # Fallbacks for local-only and shallow repositories.
        fallback_cmds = [
            ["git", "diff", "--name-only", "--diff-filter=d", "HEAD~10..HEAD", "--"] + pathspecs,
            ["git", "diff", "--name-only", "--diff-filter=d", "HEAD~1..HEAD", "--"] + pathspecs,
            [
                "git",
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "--diff-filter=d",
                "HEAD",
                "--",
            ]
            + pathspecs,
        ]
        for cmd in fallback_cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd_str)
            except (FileNotFoundError, OSError) as exc:
                raise DiffUnavailableError(f"git diff unavailable (could not execute git): {exc}") from exc
            if result.returncode == 0:
                break
        else:
            raise DiffUnavailableError(
                f"git diff failed for '{base_ref}...HEAD' and local fallbacks. Cannot determine changed files."
            )
    files = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if any(pat in line for pat in EXCLUDE_PATTERNS):
            continue
        if source_only and any(pat in line for pat in COVERAGE_EXCLUDE_PATTERNS):
            continue
        if tests_only and ("__init__.py" in line or "conftest.py" in line):
            continue
        files.append(line)
    return files
