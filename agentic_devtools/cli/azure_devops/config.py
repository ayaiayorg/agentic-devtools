"""
Azure DevOps constants and configuration.

Repository Detection:
    The repository name is determined in the following priority order:
    1. State value (if set via agdt-set repository "repo-name")
    2. Git remote detection (from `git remote get-url origin`)
    3. Hardcoded DEFAULT_REPOSITORY constant

    This allows the package to automatically detect the correct repository name
    from the git remote URL, fixing issues where the hardcoded value may be
    incorrect for different projects.

    Supported URL formats:
    - Azure DevOps: https://dev.azure.com/org/project/_git/repo-name
    - GitHub HTTPS: https://github.com/owner/repo-name.git
    - GitHub SSH: git@github.com:owner/repo-name.git
"""

import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from ...state import get_value

# =============================================================================
# Constants
# =============================================================================

DEFAULT_ORGANIZATION = "https://dev.azure.com/swica"
DEFAULT_PROJECT = "DragonflyMgmt"
DEFAULT_REPOSITORY = "agdt-platform-management"
APPROVAL_SENTINEL = "--- APPROVED ---"
API_VERSION = "7.0"


# =============================================================================
# Repository Detection
# =============================================================================


def get_repository_name_from_git_remote() -> Optional[str]:
    """
    Extract the repository name from the git remote URL.

    Supports Azure DevOps and GitHub URL formats:
    - Azure DevOps: https://dev.azure.com/org/project/_git/repo-name
    - GitHub: https://github.com/owner/repo-name.git
    - GitHub SSH: git@github.com:owner/repo-name.git

    Returns:
        Repository name if found, None otherwise.
    """
    try:
        # Get the origin remote URL
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()

        if not remote_url or not isinstance(remote_url, str):
            return None

        # Azure DevOps pattern: https://dev.azure.com/org/project/_git/repo-name
        azure_match = re.search(r"/_git/([^/?#]+)", remote_url)
        if azure_match:
            return azure_match.group(1)

        # GitHub HTTPS pattern: https://github.com/owner/repo-name.git
        github_https_match = re.search(r"github\.com[:/][\w-]+/([\w-]+?)(?:\.git)?$", remote_url)
        if github_https_match:
            return github_https_match.group(1)

        return None

    except (subprocess.CalledProcessError, FileNotFoundError, AttributeError, TypeError):
        # Git command failed, git not available, or mocked incorrectly in tests
        return None


# =============================================================================
# Configuration Dataclass
# =============================================================================


@dataclass(frozen=True)
class AzureDevOpsConfig:
    """Configuration for Azure DevOps API calls."""

    organization: str
    project: str
    repository: str
    pull_request_id: Optional[int] = None
    thread_id: Optional[int] = None

    @classmethod
    def from_state(cls) -> "AzureDevOpsConfig":
        """Create config from state values or defaults."""
        # Try to get repository from state, then git remote, then hardcoded default
        repository = get_value("repository")
        if not repository:
            repository = get_repository_name_from_git_remote() or DEFAULT_REPOSITORY

        return cls(
            organization=get_value("organization") or DEFAULT_ORGANIZATION,
            project=get_value("project") or DEFAULT_PROJECT,
            repository=repository,
        )

    def build_api_url(self, repo_id: str, *path_segments) -> str:
        """Build an Azure DevOps API URL."""
        base = f"{self.organization.rstrip('/')}/{self.project}/_apis/git/repositories/{repo_id}"
        path = "/".join(str(s) for s in path_segments)
        return f"{base}/{path}?api-version={API_VERSION}"
