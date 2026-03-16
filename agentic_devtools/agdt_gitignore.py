"""
Managed ``.agdt/.gitignore`` file for ignoring runtime state.

This module defines which paths inside ``.agdt/`` should be ignored by git
(runtime state, logs, workflows) while keeping tracked config/scripts
visible.  The constant ``AGDT_GITIGNORE_ENTRIES`` is the single source of
truth used by both ``ensure_agdt_gitignore()`` and ``stage_changes()``.
"""

from pathlib import Path
from typing import Optional

# Single source of truth for what .agdt/.gitignore should contain AND
# what stage_changes() should unstage as defense-in-depth.
AGDT_GITIGNORE_ENTRIES = ("runtime-bootstrap.json", "workflows/")

AGDT_GITIGNORE_HEADER = (
    "# Managed by agentic-devtools — do not edit manually.\n"
    "# Ignores runtime state; tracked config/scripts remain visible.\n"
)


def ensure_agdt_gitignore(git_root: Optional[Path]) -> bool:
    """Write (or overwrite) ``.agdt/.gitignore`` with the managed entries.

    The file is unconditionally overwritten each time (agdt-managed file —
    user customizations are not preserved).

    Args:
        git_root: Repository root directory.  When ``None`` the call is a
            silent no-op.

    Returns:
        ``True`` if the file was successfully created/updated, ``False``
        if *git_root* is ``None`` or a write error occurred.
    """
    if git_root is None:
        return False

    agdt_dir = git_root / ".agdt"
    gitignore_path = agdt_dir / ".gitignore"
    content = AGDT_GITIGNORE_HEADER + "\n".join(AGDT_GITIGNORE_ENTRIES) + "\n"

    try:
        agdt_dir.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False
