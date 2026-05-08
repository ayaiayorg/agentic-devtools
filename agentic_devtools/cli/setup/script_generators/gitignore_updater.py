"""``.gitignore`` updater for managed setup scripts.

Replaces ``\\.agdt/`` with ``\\.agdt/*`` (glob) and adds a negation rule
so that ``\\.agdt/agentic-devtools-*.py`` files are tracked by git.
The modification is idempotent — running it twice produces the same
result.
"""

from __future__ import annotations

from pathlib import Path

_AGDT_IGNORE_DIR = ".agdt/"
_AGDT_IGNORE_GLOB = ".agdt/*"
_AGDT_NEGATION = "!.agdt/agentic-devtools-*.py"
_AGDT_GITIGNORE_NEGATION = "!.agdt/.gitignore"


def _detect_newline(content: str) -> str:
    """Return the dominant line ending in *content* (``\\r\\n`` or ``\\n``)."""
    if "\r\n" in content:
        return "\r\n"
    return "\n"


def update_gitignore(repo_root: Path) -> str:
    """Update the root ``.gitignore`` to track managed setup scripts.

    Returns a human-readable status message.
    """
    gitignore_path = repo_root / ".gitignore"

    if not gitignore_path.is_file():
        return "  ℹ No .gitignore found — skipping."

    try:
        content = gitignore_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return f"  ⚠ Failed to read .gitignore: {exc}"

    newline = _detect_newline(content)
    lines = content.splitlines(keepends=True)
    modified = False

    # Ensure the last line is newline-terminated to prevent concatenation
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] = lines[-1] + newline

    # Replace ".agdt/" with ".agdt/*"
    new_lines: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n\r")
        if stripped == _AGDT_IGNORE_DIR:
            new_lines.append(_AGDT_IGNORE_GLOB + newline)
            modified = True
        else:
            new_lines.append(line)

    # Deduplicate .agdt/* lines (can occur when both .agdt/ and .agdt/* existed)
    seen_glob = False
    deduped_lines: list[str] = []
    for line in new_lines:
        if line.rstrip("\n\r") == _AGDT_IGNORE_GLOB:
            if seen_glob:
                modified = True
                continue
            seen_glob = True
        deduped_lines.append(line)
    new_lines = deduped_lines

    # Ensure .agdt/* line exists (if neither .agdt/ nor .agdt/* was present)
    has_glob = any(line.rstrip("\n\r") == _AGDT_IGNORE_GLOB for line in new_lines)
    if not has_glob:
        # Append at end
        new_lines.append(_AGDT_IGNORE_GLOB + newline)
        modified = True

    # Add negation if not already present
    has_negation = any(line.rstrip("\n\r") == _AGDT_NEGATION for line in new_lines)
    if not has_negation:
        # Insert negation right after the .agdt/* line
        idx = None
        for i, line in enumerate(new_lines):
            if line.rstrip("\n\r") == _AGDT_IGNORE_GLOB:
                idx = i
                break
        if idx is not None:
            new_lines.insert(idx + 1, _AGDT_NEGATION + newline)
        else:
            new_lines.append(_AGDT_NEGATION + newline)
        modified = True

    # Add .gitignore negation if not already present
    has_gitignore_negation = any(line.rstrip("\n\r") == _AGDT_GITIGNORE_NEGATION for line in new_lines)
    if not has_gitignore_negation:
        # Insert after the managed scripts negation rule
        idx = None
        for i, line in enumerate(new_lines):
            if line.rstrip("\n\r") == _AGDT_NEGATION:
                idx = i
                break
        if idx is not None:
            new_lines.insert(idx + 1, _AGDT_GITIGNORE_NEGATION + newline)
        else:
            new_lines.append(_AGDT_GITIGNORE_NEGATION + newline)
        modified = True

    if not modified:
        return "  ✓ .gitignore already up to date."

    try:
        gitignore_path.write_text("".join(new_lines), encoding="utf-8")
    except OSError as exc:
        return f"  ⚠ Failed to write .gitignore: {exc}"

    return "  ✓ .gitignore updated to track managed setup scripts."
