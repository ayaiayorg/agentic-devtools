"""
Azure DevOps constants and configuration.
"""

from dataclasses import dataclass
from typing import Optional

from ...state import get_value

# =============================================================================
# Constants
# =============================================================================

DEFAULT_ORGANIZATION = "https://dev.azure.com/swica"
DEFAULT_PROJECT = "DragonflyMgmt"
DEFAULT_REPOSITORY = "dfly-platform-management"
APPROVAL_SENTINEL = "--- APPROVED ---"
API_VERSION = "7.0"


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
        return cls(
            organization=get_value("organization") or DEFAULT_ORGANIZATION,
            project=get_value("project") or DEFAULT_PROJECT,
            repository=get_value("repository") or DEFAULT_REPOSITORY,
        )

    def build_api_url(self, repo_id: str, *path_segments) -> str:
        """Build an Azure DevOps API URL."""
        base = f"{self.organization.rstrip('/')}/{self.project}/_apis/git/repositories/{repo_id}"
        path = "/".join(str(s) for s in path_segments)
        return f"{base}/{path}?api-version={API_VERSION}"
