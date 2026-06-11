"""
Dedicated commit-body.md reader for commit message body management.

This module provides functions to read and parse a per-worktree
``commit-body.md`` file that lives at::

    .agdt/workflows/{identity}/{worktree_key}/files/commit-body.md

The file supports optional YAML frontmatter delimited by ``---`` lines.
Only the body text (after frontmatter) is injected into the git commit
message; the frontmatter is available for tooling/agents via
``parse_frontmatter()`` or the ``agdt-commit-body-show`` command.

Constants:
    MAX_BODY_FILE_SIZE: Hard limit (100 KB) on the commit-body.md file.
    COMMIT_BODY_FILENAME: Name of the body file (``commit-body.md``).
    FILES_SUBDIR: Subdirectory within the state dir (``files``).
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ...state import get_state_dir

MAX_BODY_FILE_SIZE = 102_400  # 100 KB hard limit
COMMIT_BODY_FILENAME = "commit-body.md"
FILES_SUBDIR = "files"


@dataclass
class CommitBodyResult:
    """Result of reading the commit-body.md file.

    Attributes:
        body: Body text after optional frontmatter (may be empty or whitespace-only).
        frontmatter: Parsed YAML frontmatter (empty dict if none/malformed).
        path: Resolved absolute path to the commit-body.md file.
        file_exists: Whether the file exists on disk.
        error: Error message if a hard failure occurred (e.g., >100KB, non-UTF-8).
        warning: Warning message (e.g., malformed/non-mapping frontmatter or missing closing delimiter).
    """

    body: str = ""
    frontmatter: dict = field(default_factory=dict)
    path: Path = field(default_factory=lambda: Path())
    file_exists: bool = False
    error: str = ""
    warning: str = ""


def get_commit_body_path() -> Path:
    """Return the absolute path to the commit-body.md file.

    The path is ``{state_dir}/files/commit-body.md``.

    Returns:
        Absolute Path to the commit-body.md file.
    """
    return (get_state_dir() / FILES_SUBDIR / COMMIT_BODY_FILENAME).resolve()


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse optional YAML frontmatter from content.

    Frontmatter is delimited by ``---`` on its own line at the very start
    of the content and closed by another ``---`` line. If no valid
    frontmatter is detected the entire content is returned as body.

    Args:
        content: The raw file content (BOM already stripped).

    Returns:
        A tuple of (frontmatter_dict, body_text). If frontmatter is
        absent or malformed, frontmatter_dict is ``{}`` and body_text
        is the full content (for malformed) or content sans frontmatter
        block (for valid).

    Raises:
        No exceptions raised; malformed YAML results in empty dict and
        a warning is printed to stderr.
    """
    first_line = content.split("\n", 1)[0]
    if first_line.strip() != "---":
        return {}, content

    # Find closing ---
    lines = content.split("\n")
    # First line is '---', look for closing '---'
    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        print(
            "Warning: YAML frontmatter opening delimiter found but no closing "
            "'---' delimiter; treating entire file as body.",
            file=sys.stderr,
        )
        return {}, content

    # Extract frontmatter YAML and body
    fm_text = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :])

    # Parse YAML
    try:
        parsed = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        # Malformed YAML — warn and return entire content as body
        print(
            "Warning: Malformed YAML frontmatter in commit-body.md. Treating entire file as body.",
            file=sys.stderr,
        )
        return {}, content

    # None result (empty frontmatter block) → treat as empty dict
    if parsed is None:
        return {}, body

    # Non-dict result (e.g., scalar or list) → malformed
    if not isinstance(parsed, dict):
        print(
            "Warning: YAML frontmatter is not a mapping (dict). Treating entire file as body.",
            file=sys.stderr,
        )
        return {}, content

    return parsed, body


def extract_title(message: str) -> str:
    """Extract the first line of a commit message as the title.

    Args:
        message: The full commit message (may be multiline).

    Returns:
        The first line only, stripped of trailing whitespace.
    """
    first_line = message.split("\n", 1)[0]
    return first_line.rstrip()


def assemble_message(title: str, body: str) -> str:
    """Assemble a commit message from title and body.

    Produces: ``title + blank_line + body`` per git convention.

    Args:
        title: The commit title (first line).
        body: The commit body text.

    Returns:
        Assembled commit message string.
    """
    return f"{title}\n\n{body}"


def read_commit_body() -> CommitBodyResult:
    """Read the commit-body.md file from the current worktree state dir.

    Handles:
    - Missing file or missing ``files/`` directory → absent body (no error)
    - Empty file → empty body (no error), file_exists=True
    - Whitespace-only file → body is preserved (callers may treat as absent via ``.strip()``)
    - File >100KB → hard error
        - BOM stripping
        - YAML frontmatter parsing (malformed → warning, body preserved)

        Returns:
            CommitBodyResult with body text, frontmatter, and metadata.
    """
    path = get_commit_body_path()
    result = CommitBodyResult(path=path)

    if not path.exists():
        return result

    result.file_exists = True

    # Check file size
    try:
        size = path.stat().st_size
    except OSError as e:
        result.error = f"Cannot stat commit-body.md: {e}"
        return result

    if size > MAX_BODY_FILE_SIZE:
        result.error = f"commit-body.md exceeds maximum size ({size:,} bytes > {MAX_BODY_FILE_SIZE:,} bytes)"
        return result

    # Read file
    try:
        raw = path.read_bytes()
    except OSError as e:
        result.error = f"Cannot read commit-body.md: {e}"
        return result

    # Strip BOM
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]

    # Decode UTF-8
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        result.error = f"commit-body.md is not valid UTF-8: {e}"
        return result

    # Normalize line endings to LF (git uses LF in commit messages)
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Parse frontmatter
    frontmatter, body = parse_frontmatter(content)
    result.frontmatter = frontmatter
    result.body = body

    # If frontmatter was malformed, we got {} and full content as body,
    # but the warning was already printed by parse_frontmatter.
    # Detect this case: frontmatter is empty but content started with ---
    # If we started with a frontmatter delimiter but parsing did not strip it,
    # treat that as a warning signal (malformed YAML or missing closing delimiter).
    if content.startswith("---") and not frontmatter and body == content:
        result.warning = "YAML frontmatter could not be parsed or is not a mapping."

    return result


def show_cmd() -> None:
    """Print the commit-body.md content for inspection.

    Output format:
    - Header with file path and character count
    - Frontmatter section (if present)
    - Body section

    Exit codes:
    - 0: Success (file exists and was read)
    - 1: File missing or hard error (>100KB, non-UTF-8)
    """
    body_result = read_commit_body()

    if body_result.error:
        print(f"Error: {body_result.error}", file=sys.stderr)
        sys.exit(1)

    if not body_result.file_exists:
        print(
            f"Error: commit-body.md not found at {body_result.path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Force UTF-8 stdout so box-drawing characters survive on Windows cp1252 terminals.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Header
    body_len = len(body_result.body)
    fm_keys = len(body_result.frontmatter)
    fm_status = f"yes ({fm_keys} keys)" if fm_keys > 0 else "no"

    separator = "═" * 66
    print(separator)
    print(f"COMMIT BODY: {body_result.path}")
    print(f"Length: {body_len:,} characters")
    print(f"Frontmatter: {fm_status}")
    print(separator)

    # Frontmatter section
    if body_result.frontmatter:
        print()
        print("--- Frontmatter ---")
        for key, value in body_result.frontmatter.items():
            print(f"{key}: {value!r}")

    # Body section
    print()
    print("--- Body ---")
    print(body_result.body)
