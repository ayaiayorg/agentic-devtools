"""Tests for constants."""
from agentic_devtools.cli import azure_devops


class TestConstants:
    """Tests for module constants."""

    def test_default_organization(self):
        """Test default organization URL."""
        assert azure_devops.DEFAULT_ORGANIZATION == "https://dev.azure.com/swica"

    def test_default_project(self):
        """Test default project."""
        assert azure_devops.DEFAULT_PROJECT == "DragonflyMgmt"

    def test_default_repository(self):
        """Test default repository."""
        assert azure_devops.DEFAULT_REPOSITORY == "dfly-platform-management"

    def test_approval_sentinel(self):
        """Test approval sentinel constant."""
        assert azure_devops.APPROVAL_SENTINEL == "--- APPROVED ---"

    def test_api_version(self):
        """Test API version constant."""
        assert azure_devops.API_VERSION == "7.0"
