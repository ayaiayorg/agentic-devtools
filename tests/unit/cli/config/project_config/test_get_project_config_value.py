"""Tests for get_project_config_value function."""

from unittest.mock import patch

from agentic_devtools.cli.config.project_config import get_project_config_value


class TestGetProjectConfigValue:
    """Tests for get_project_config_value function."""

    @patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={"jira_base_url": "https://jira.example.com"})
    def test_returns_existing_key(self, _mock_load):
        """Should return value for an existing key."""
        result = get_project_config_value("jira_base_url")
        assert result == "https://jira.example.com"

    @patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={})
    def test_returns_none_for_missing_key(self, _mock_load):
        """Should return None when key is not in config."""
        result = get_project_config_value("nonexistent")
        assert result is None

    @patch("agentic_devtools.cli.config.project_config.load_project_config", return_value={})
    def test_returns_none_when_no_config(self, _mock_load):
        """Should return None when config is empty."""
        result = get_project_config_value("jira_project_keys")
        assert result is None
