"""
Tests for Jira configuration and authentication.
"""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import jira


class TestJiraConfiguration:
    """Tests for Jira configuration functions."""

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    def test_raises_when_unconfigured(self, _mock_config, temp_state_dir, clear_state_before):
        """Test raises ValueError when no Jira base URL is configured."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Jira base URL not configured"):
                jira.get_jira_base_url()

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    def test_jira_base_url_from_env(self, _mock_config, temp_state_dir, clear_state_before):
        """Test Jira base URL from environment."""
        with patch.dict("os.environ", {"JIRA_BASE_URL": "https://custom.jira.com"}):
            url = jira.get_jira_base_url()
            assert url == "https://custom.jira.com"

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    def test_jira_base_url_from_state(self, _mock_config, temp_state_dir, clear_state_before):
        """Test Jira base URL from state takes precedence."""
        state.set_value("jira_base_url", "https://state.jira.com")
        with patch.dict("os.environ", {"JIRA_BASE_URL": "https://env.jira.com"}):
            url = jira.get_jira_base_url()
            assert url == "https://state.jira.com"

    @patch(
        "agentic_devtools.cli.config.project_config.get_project_config_value", return_value="https://config.jira.com"
    )
    def test_jira_base_url_from_project_config(self, _mock_config, temp_state_dir, clear_state_before):
        """Test Jira base URL from project config takes highest precedence."""
        state.set_value("jira_base_url", "https://state.jira.com")
        with patch.dict("os.environ", {"JIRA_BASE_URL": "https://env.jira.com"}):
            url = jira.get_jira_base_url()
            assert url == "https://config.jira.com"
