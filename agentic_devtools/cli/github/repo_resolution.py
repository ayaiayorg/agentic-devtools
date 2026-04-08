"""GitHub repository resolution utilities.

Resolves ``owner/repo`` from CLI arguments, state, or git remote URL.
Shared by all ``agdt-gh-*`` commands.
"""

import re
import sys

from ...state import get_value
from ..subprocess_utils import run_safe

# GitHub remote URL patterns
_GITHUB_HTTPS_RE = re.compile(r"github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?$")
_GITHUB_SSH_RE = re.compile(r"git@github\.com:([\w.-]+)/([\w.-]+?)(?:\.git)?$")


def _resolve_repo_from_git_remote() -> str | None:
    """Attempt to derive ``owner/repo`` from the git origin remote URL."""
    try:
        result = run_safe(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        url = result.stdout.strip()
    except OSError:
        return None

    for pattern in (_GITHUB_HTTPS_RE, _GITHUB_SSH_RE):
        m = pattern.search(url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"

    return None


def _validate_repo_format(repo: str) -> str | None:
    """Return normalized ``owner/repo`` if valid, else ``None``."""
    repo = repo.strip()
    if repo.endswith(".git"):
        repo = repo[:-4]
    parts = repo.split("/")
    if len(parts) == 2 and all(parts):
        return repo
    return None


def resolve_github_repo(cli_repo: str | None = None) -> str:
    """Resolve GitHub ``owner/repo`` from CLI arg, state, or git remote.

    Resolution order:
    1. Explicit *cli_repo* argument (``--repo`` flag).
    2. ``github.repo`` state key.
    3. Git ``origin`` remote URL.

    Calls ``sys.exit(1)`` when resolution fails.
    """
    if cli_repo:
        validated = _validate_repo_format(cli_repo)
        if validated:
            return validated
        print(
            f"Error: Invalid --repo format: {cli_repo!r}. Expected 'owner/repo'.",
            file=sys.stderr,
        )
        sys.exit(1)

    state_repo = get_value("github.repo")
    if state_repo and isinstance(state_repo, str):
        validated = _validate_repo_format(state_repo)
        if validated:
            return validated
        # State has a value but it's malformed — fall through to git remote

    remote_repo = _resolve_repo_from_git_remote()
    if remote_repo:
        return remote_repo

    print(
        "Error: Could not determine GitHub repository. "
        "Provide --repo owner/repo, set github.repo in state, "
        "or ensure a GitHub origin remote is configured.",
        file=sys.stderr,
    )
    sys.exit(1)
