"""Tests for _parse_azure_devops_context_from_remote_url."""

from agentic_devtools.cli.azure_devops.config import _parse_azure_devops_context_from_remote_url


class TestParseAzureDevopsContextFromRemoteUrl:
    """Tests for _parse_azure_devops_context_from_remote_url function."""

    def test_decodes_percent_encoded_project_and_repository(self):
        """Test that percent-encoded segments in project and repository are decoded."""
        url = "https://dev.azure.com/myorg/My%20Project/_git/My%20Repo"
        result = _parse_azure_devops_context_from_remote_url(url)
        assert result == ("https://dev.azure.com/myorg", "My Project", "My Repo")

    def test_decodes_percent_encoded_legacy_url(self):
        """Test that percent-encoded segments are decoded for legacy visualstudio.com URLs."""
        url = "https://myorg.visualstudio.com/My%20Project/_git/My%20Repo"
        result = _parse_azure_devops_context_from_remote_url(url)
        assert result == ("https://dev.azure.com/myorg", "My Project", "My Repo")

    def test_decodes_percent_encoded_ssh_url(self):
        """Test that percent-encoded segments are decoded for SSH URLs."""
        url = "git@ssh.dev.azure.com:v3/myorg/My%20Project/My%20Repo"
        result = _parse_azure_devops_context_from_remote_url(url)
        assert result == ("https://dev.azure.com/myorg", "My Project", "My Repo")

    def test_returns_none_for_non_azure_url(self):
        """Test that non-Azure DevOps URLs return None."""
        url = "https://github.com/owner/repo.git"
        result = _parse_azure_devops_context_from_remote_url(url)
        assert result is None

    def test_plain_segments_unchanged(self):
        """Test that URLs without percent-encoding still work correctly."""
        url = "https://dev.azure.com/swica/DragonflyMgmt/_git/dfly-platform-management"
        result = _parse_azure_devops_context_from_remote_url(url)
        assert result == ("https://dev.azure.com/swica", "DragonflyMgmt", "dfly-platform-management")
