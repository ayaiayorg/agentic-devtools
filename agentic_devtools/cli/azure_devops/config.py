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
    - Azure DevOps HTTPS: https://dev.azure.com/org/project/_git/repo-name
    - Azure DevOps HTTPS (authenticated): https://user@dev.azure.com/org/project/_git/repo-name
    - Azure DevOps HTTPS (legacy): https://org.visualstudio.com/project/_git/repo-name
    - Azure DevOps SSH: git@ssh.dev.azure.com:v3/org/project/repo-name
    - Azure DevOps SSH (legacy): org@vs-ssh.visualstudio.com:v3/org/project/repo-name
    - GitHub HTTPS: https://github.com/owner/repo-name.git
    - GitHub SSH: git@github.com:owner/repo-name.git
"""

import re
import subprocess
from dataclasses import dataclass
from urllib.parse import unquote

from ...state import get_value

# =============================================================================
# Constants
# =============================================================================

DEFAULT_ORGANIZATION = "https://dev.azure.com/example-org"
DEFAULT_PROJECT = "ExampleProject"
DEFAULT_REPOSITORY = "example-repo-name"
API_VERSION = "7.0"
PR_ITERATION_CHANGES_API_VERSION = "7.1-preview.1"


# =============================================================================
# Repository Detection
# =============================================================================


def _get_git_origin_remote_url() -> str | None:
    """Return the origin remote URL if available."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()
        if not remote_url or not isinstance(remote_url, str):
            return None
        return remote_url
    except (subprocess.CalledProcessError, FileNotFoundError, AttributeError, TypeError):
        return None


def _parse_azure_devops_context_from_remote_url(remote_url: str) -> tuple[str, str, str] | None:
    """Extract Azure DevOps organization, project, and repository from a remote URL."""
    azure_https_match = re.search(
        r"^https://(?:[^@/]+@)?dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/?#]+)",
        remote_url,
    )
    if azure_https_match:
        organization_name, project, repository = azure_https_match.groups()
        return (f"https://dev.azure.com/{organization_name}", unquote(project), unquote(repository))

    legacy_azure_https_match = re.search(
        r"^https://([^.]+)\.visualstudio\.com/([^/]+)/_git/([^/?#]+)",
        remote_url,
    )
    if legacy_azure_https_match:
        organization_name, project, repository = legacy_azure_https_match.groups()
        return (f"https://dev.azure.com/{organization_name}", unquote(project), unquote(repository))

    azure_ssh_match = re.search(
        r"(?:ssh\.dev\.azure\.com|vs-ssh\.visualstudio\.com):v3/([^/]+)/([^/]+)/([^/\s]+?)(?:\.git)?$",
        remote_url,
    )
    if azure_ssh_match:
        organization_name, project, repository = azure_ssh_match.groups()
        return (f"https://dev.azure.com/{organization_name}", unquote(project), unquote(repository))

    return None


def get_azure_devops_context_from_git_remote() -> tuple[str, str, str] | None:
    """
    Extract Azure DevOps organization, project, and repository from the git remote URL.

    Returns:
        Tuple of (organization_url, project, repository) for Azure DevOps remotes,
        or None for non-Azure-DevOps remotes and lookup failures.
    """
    remote_url = _get_git_origin_remote_url()
    if not remote_url:
        return None

    return _parse_azure_devops_context_from_remote_url(remote_url)


def get_repository_name_from_git_remote() -> str | None:
    """
    Extract the repository name from the git remote URL.

    Supports Azure DevOps and GitHub URL formats:
    - Azure DevOps HTTPS: https://dev.azure.com/org/project/_git/repo-name
    - Azure DevOps HTTPS (authenticated): https://user@dev.azure.com/org/project/_git/repo-name
    - Azure DevOps HTTPS (legacy): https://org.visualstudio.com/project/_git/repo-name
    - Azure DevOps SSH: git@ssh.dev.azure.com:v3/org/project/repo-name
    - Azure DevOps SSH (legacy): org@vs-ssh.visualstudio.com:v3/org/project/repo-name
    - GitHub HTTPS: https://github.com/owner/repo-name.git
    - GitHub SSH: git@github.com:owner/repo-name.git

    Percent-encoded segments (e.g. ``My%20Project``) are decoded automatically.

    Returns:
        Repository name if found, None otherwise.
    """
    remote_url = _get_git_origin_remote_url()
    if not remote_url:
        return None

    azure_devops_context = _parse_azure_devops_context_from_remote_url(remote_url)
    if azure_devops_context:
        return azure_devops_context[2]

    # GitHub HTTPS pattern: https://github.com/owner/repo-name.git
    github_https_match = re.search(r"github\.com[:/][\w-]+/([\w-]+?)(?:\.git)?$", remote_url)
    if github_https_match:
        return github_https_match.group(1)

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
    pull_request_id: int | None = None
    thread_id: int | None = None

    @classmethod
    def from_state(cls) -> "AzureDevOpsConfig":
        """Create config from state values or defaults."""
        remote_context = get_azure_devops_context_from_git_remote()
        remote_organization = remote_context[0] if remote_context else None
        remote_project = remote_context[1] if remote_context else None
        remote_repository = remote_context[2] if remote_context else None

        # Only call get_repository_name_from_git_remote() when remote_context is None
        # (i.e., non-Azure-DevOps remote such as GitHub) to avoid running
        # `git remote get-url origin` twice on every config load.
        repository_from_git_remote = None if remote_context else get_repository_name_from_git_remote()

        repository = get_value("repository") or remote_repository or repository_from_git_remote or DEFAULT_REPOSITORY
        organization = get_value("organization") or remote_organization or DEFAULT_ORGANIZATION
        project = get_value("project") or remote_project or DEFAULT_PROJECT

        return cls(
            organization=organization,
            project=project,
            repository=repository,
        )

    def build_api_url(self, repo_id: str, *path_segments) -> str:
        """Build an Azure DevOps API URL."""
        base = f"{self.organization.rstrip('/')}/{self.project}/_apis/git/repositories/{repo_id}"
        path = "/".join(str(s) for s in path_segments)
        return f"{base}/{path}?api-version={API_VERSION}"
