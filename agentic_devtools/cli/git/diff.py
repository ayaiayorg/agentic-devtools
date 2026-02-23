"""
Git diff helper functions for extracting change information.

These helpers run Git commands to extract diff information between refs,
useful for PR analysis and code review workflows.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

from ..subprocess_utils import run_safe


@dataclass
class DiffEntry:
    """Represents a single file change in a git diff."""

    path: str
    status: str
    change_type: str
    original_path: Optional[str] = None


@dataclass
class AddedLine:
    """Represents an added line in a diff."""

    line_number: int
    content: str


@dataclass
class AddedLinesInfo:
    """Information about added lines in a file diff."""

    lines: List[AddedLine]
    is_binary: bool


def normalize_ref_name(ref: Optional[str]) -> Optional[str]:
    """
    Normalize a git ref by stripping refs/heads/ prefix.

    Args:
        ref: Git reference like "refs/heads/main" or "main"

    Returns:
        Normalized ref name like "main", or None if input is None/empty.
    """
    if not ref:
        return None
    if ref.startswith("refs/heads/"):
        return ref[11:]  # len("refs/heads/") == 11
    return ref


def sync_git_ref(ref: str) -> bool:
    """
    Fetch a git ref from origin if it doesn't exist locally.

    Args:
        ref: Git reference to sync.

    Returns:
        True if sync succeeded or ref exists, False otherwise.
    """
    if not ref:
        return False

    # Check if ref exists locally
    result = run_safe(["git", "rev-parse", "--verify", ref], capture_output=True, text=True)

    if result.returncode == 0:
        return True

    # Fetch from origin
    fetch_ref = ref
    if ref.startswith("origin/"):
        fetch_ref = ref[7:]  # Remove "origin/" prefix

    result = run_safe(["git", "fetch", "origin", fetch_ref], capture_output=True, text=True)
    return result.returncode == 0


def get_diff_entries(base_ref: str, compare_ref: str) -> List[DiffEntry]:
    """
    Get file change entries between two git refs.

    Args:
        base_ref: Base commit/branch for comparison.
        compare_ref: Compare commit/branch.

    Returns:
        List of DiffEntry objects describing changes.
    """
    result = run_safe(
        ["git", "diff", "--name-status", "--find-renames", base_ref, compare_ref],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    entries = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0]
        if status.startswith("R"):  # Rename
            entries.append(
                DiffEntry(
                    path=parts[2] if len(parts) >= 3 else parts[-1],
                    status=status,
                    change_type="R",
                    original_path=parts[1] if len(parts) >= 2 else None,
                )
            )
        else:
            entries.append(DiffEntry(path=parts[1], status=status, change_type=status[0]))

    return entries


def get_added_lines_info(base_ref: str, compare_ref: str, path: str) -> AddedLinesInfo:
    """
    Get information about added lines for a specific file.

    Args:
        base_ref: Base commit/branch.
        compare_ref: Compare commit/branch.
        path: File path (repo-root-relative).

    Returns:
        AddedLinesInfo with line details and binary flag.
    """
    # Use :/ prefix to make path repo-root-relative (works from any subdirectory)
    repo_path = f":/{path}"
    result = run_safe(
        ["git", "diff", "--no-color", "--unified=0", base_ref, compare_ref, "--", repo_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return AddedLinesInfo(lines=[], is_binary=False)

    output_lines = result.stdout.split("\n")

    # Check for binary file — the marker may appear after a "diff --git" header
    if any(line.startswith("Binary files") for line in output_lines):
        return AddedLinesInfo(lines=[], is_binary=True)

    added_lines = []
    current_line = 0

    for raw_line in output_lines:
        # Parse hunk header: @@ -X,Y +A,B @@
        if raw_line.startswith("@@ "):
            match = re.match(r"@@ [^+]*\+(\d+)(?:,(\d+))? @@", raw_line)
            if match:
                current_line = int(match.group(1))
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines.append(
                AddedLine(
                    line_number=current_line,
                    content=raw_line[1:],  # Strip leading +
                )
            )
            current_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            # Removed line, don't increment
            continue
        elif raw_line.startswith(" "):
            current_line += 1

    return AddedLinesInfo(lines=added_lines, is_binary=False)


def get_diff_patch(base_ref: str, compare_ref: str, path: str) -> Optional[str]:
    """
    Get the full diff patch for a specific file.

    Args:
        base_ref: Base commit/branch.
        compare_ref: Compare commit/branch.
        path: File path (repo-root-relative).

    Returns:
        Diff patch as string, or None if no changes.
    """
    # Use :/ prefix to make path repo-root-relative (works from any subdirectory)
    repo_path = f":/{path}"
    result = run_safe(
        ["git", "diff", "--no-color", base_ref, compare_ref, "--", repo_path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return None

    return result.stdout.strip()
