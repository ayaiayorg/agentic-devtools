"""Diff heuristic for verifying thread resolution.

Provides a lightweight check to determine whether specific file lines
were modified in the PR diff, used as a proxy for whether review comments
have been addressed.
"""

from __future__ import annotations

import re

# Matches unified diff hunk headers: @@ -old_start,old_count +new_start,new_count @@
_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")


def check_lines_modified(
    diff_text: str,
    path: str,
    start_line: int | None,
    end_line: int | None,
) -> bool:
    """Check if specific lines in a file were modified according to a diff.

    Parses unified diff format and checks whether the given line range
    overlaps with any added/modified lines in the specified file.

    Args:
        diff_text: Full unified diff text.
        path: File path to check (relative to repo root).
        start_line: Start line to check (1-based). None means PR-level comment.
        end_line: End line to check (1-based). None defaults to start_line.

    Returns:
        True if the lines were modified, False otherwise.
        Returns False for PR-level comments (start_line is None).
    """
    if start_line is None:
        return False

    if end_line is None:
        end_line = start_line

    # Find the diff section for the target file
    in_target_file = False
    modified_lines: set[int] = set()
    current_line = 0

    for line in diff_text.splitlines():
        # Detect file diff headers
        if line.startswith("diff --git"):
            # Check if this diff section is for our target file
            # Format: diff --git a/path b/path
            header_match = _DIFF_HEADER_RE.match(line)
            if header_match:
                in_target_file = header_match.group(2) == path
            else:
                in_target_file = False
            continue

        if not in_target_file:
            continue

        # Parse hunk header to get the starting line number
        hunk_match = _HUNK_HEADER_RE.match(line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        # Track modified lines (additions and modifications)
        if line.startswith("+") and not line.startswith("+++"):
            modified_lines.add(current_line)
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            # Deletions don't advance the new-file line counter
            pass
        else:
            # Context line
            current_line += 1

    # Check overlap between modified lines and the target range
    target_range = set(range(start_line, end_line + 1))
    return bool(modified_lines & target_range)
