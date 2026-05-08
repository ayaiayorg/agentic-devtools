"""Repo-root detection helper.

Provides ``get_git_repo_root()`` which shells out to ``git rev-parse``
so that generated-script logic can locate the repository root without
importing ``agentic_devtools.state``.
"""

import subprocess
from pathlib import Path


def get_git_repo_root() -> Path | None:
    """Return the repository root, or ``None`` outside a git work-tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
