"""
GitHub repository resolution utilities.

Resolves ``owner/repo`` from CLI arguments, state, or the ``origin`` git
remote URL.  Shared by all ``agdt-gh-*`` commands.
"""

import re
import sys

from ...state import get_value
from ..subprocess_utils import run_safe

# GitHub: https://github.com/owner/repo.git  or  git@github.com:owner/repo.git
_GITHUB_REMOTE_RE = re.compile(
    r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?$",
)


def _get_git_origin_url() -> str | None:
    """Return the ``origin`` remote URL, or ``None`` on failure."""
    try:
        result = run_safe(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        return url if url else None
    except (FileNotFoundError, OSError):
        return None


def _parse_github_remote_url(url: str) -> str | None:
    """Extract ``owner/repo`` from a GitHub remote *url*, or ``None``."""
    m = _GITHUB_REMOTE_RE.search(url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return None


def resolve_github_repo(cli_repo: str | None = None) -> str:
    """Resolve ``owner/repo`` from CLI arg, state, or git remote.

    Resolution priority:
    1. *cli_repo* (if non-empty after strip)
    2. ``github.repo`` from state
    3. Auto-detect from ``git remote get-url origin``

    Exits with code 1 if resolution fails.
    """
    if cli_repo and cli_repo.strip():
        return cli_repo.strip()

    state_repo = get_value("github.repo")
    if state_repo and isinstance(state_repo, str) and state_repo.strip():
        return state_repo.strip()

    origin_url = _get_git_origin_url()
    if origin_url:
        parsed = _parse_github_remote_url(origin_url)
        if parsed:
            return parsed

    print(
        "Error: Could not determine GitHub repository. "
        "Provide --repo owner/repo, set github.repo in state, "
        "or ensure a GitHub origin remote is configured.",
        file=sys.stderr,
    )
    sys.exit(1)
