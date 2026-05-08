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


def update_gitignore(repo_root: Path) -> str:
    """Update the root ``.gitignore`` to track managed setup scripts.

    Returns a human-readable status message.
    """
    gitignore_path = repo_root / ".gitignore"

    if not gitignore_path.is_file():
        return "  ℹ No .gitignore found — skipping."

    try:
        content = gitignore_path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"  ⚠ Failed to read .gitignore: {exc}"

    lines = content.splitlines(keepends=True)
    modified = False

    # Replace ".agdt/" with ".agdt/*"
    new_lines: list[str] = []
    for line in lines:
        stripped = line.rstrip("\n\r")
        if stripped == _AGDT_IGNORE_DIR:
            new_lines.append(_AGDT_IGNORE_GLOB + "\n")
            modified = True
        else:
            new_lines.append(line)

    # Ensure .agdt/* line exists (if neither .agdt/ nor .agdt/* was present)
    has_glob = any(line.rstrip("\n\r") == _AGDT_IGNORE_GLOB for line in new_lines)
    if not has_glob:
        # Append after last non-empty line or at end
        new_lines.append(_AGDT_IGNORE_GLOB + "\n")
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
            new_lines.insert(idx + 1, _AGDT_NEGATION + "\n")
        else:
            new_lines.append(_AGDT_NEGATION + "\n")
        modified = True

    if not modified:
        return "  ✓ .gitignore already up to date."

    try:
        gitignore_path.write_text("".join(new_lines), encoding="utf-8")
    except OSError as exc:
        return f"  ⚠ Failed to write .gitignore: {exc}"

    return "  ✓ .gitignore updated to track managed setup scripts."
