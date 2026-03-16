"""
Manages the ``.agdt/.gitignore`` file that prevents runtime state from being
committed on code branches.

The constant ``AGDT_GITIGNORE_ENTRIES`` is the single source of truth for:
1. The entries written to ``.agdt/.gitignore``.
2. The paths unstaged by ``stage_changes()`` in ``cli/git/operations.py``.
"""

from pathlib import Path
from typing import Optional

# Paths (relative to .agdt/) that must be git-ignored on code branches.
# Used both for writing .agdt/.gitignore and for defense-in-depth unstaging
# in stage_changes().
AGDT_GITIGNORE_ENTRIES = ("runtime-bootstrap.json", "workflows/")

AGDT_GITIGNORE_HEADER = (
    "# Managed by agentic-devtools — do not edit manually.\n"
    "# Ignores runtime state; tracked config/scripts remain visible.\n"
)


def ensure_agdt_gitignore(git_root: Optional[Path]) -> bool:
    """Write (or overwrite) ``.agdt/.gitignore`` with the managed entries.

    Args:
        git_root: Repository/worktree root.  When ``None`` (not in a git
            repo) the call is a silent no-op.

    Returns:
        ``True`` when the file was successfully created/updated,
        ``False`` when *git_root* is ``None`` or a write error occurred.
    """
    if git_root is None:
        return False

    content = AGDT_GITIGNORE_HEADER + "\n".join(AGDT_GITIGNORE_ENTRIES) + "\n"
    gitignore_path = git_root / ".agdt" / ".gitignore"
    try:
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False
