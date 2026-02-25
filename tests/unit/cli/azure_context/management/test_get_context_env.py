"""Tests for get_context_env function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import get_context_env


class TestGetContextEnv:
    """Tests for get_context_env function."""

    def test_returns_azure_config_dir_key(self, tmp_path):
        """Should return a dict containing AZURE_CONFIG_DIR key."""
        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            result = get_context_env(AzureContext.DEVOPS)

        assert "AZURE_CONFIG_DIR" in result

    def test_azure_config_dir_contains_devops(self, tmp_path):
        """AZURE_CONFIG_DIR value should contain 'devops' for DEVOPS context."""
        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            result = get_context_env(AzureContext.DEVOPS)

        assert "devops" in result["AZURE_CONFIG_DIR"]

    def test_azure_config_dir_contains_resources(self, tmp_path):
        """AZURE_CONFIG_DIR value should contain 'resources' for AZURE_RESOURCES context."""
        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            result = get_context_env(AzureContext.AZURE_RESOURCES)

        assert "resources" in result["AZURE_CONFIG_DIR"]

    def test_returns_dict(self, tmp_path):
        """Return value should be a dictionary."""
        with patch("agentic_devtools.cli.azure_context.config.Path.home", return_value=tmp_path):
            result = get_context_env(AzureContext.DEVOPS)

        assert isinstance(result, dict)
