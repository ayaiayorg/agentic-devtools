"""Tests for get_jira_project_keys function."""

import os
from unittest.mock import patch

from agentic_devtools.cli.jira.config import get_jira_project_keys


class TestGetJiraProjectKeys:
    """Tests for get_jira_project_keys function."""

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value="ACME,PROJ")
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_keys_from_project_config(self, _mock_state, _mock_config):
        """Should return keys from project config."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_jira_project_keys()
        assert result == ["ACME", "PROJ"]

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value="MYPROJ")
    def test_returns_keys_from_state(self, _mock_state, _mock_config):
        """Should fall back to state value."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_jira_project_keys()
        assert result == ["MYPROJ"]

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_keys_from_env(self, _mock_state, _mock_config):
        """Should fall back to env var."""
        with patch.dict(os.environ, {"JIRA_PROJECT_KEYS": "ENV1,ENV2"}):
            result = get_jira_project_keys()
        assert result == ["ENV1", "ENV2"]

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_empty_list_when_unconfigured(self, _mock_state, _mock_config):
        """Should return empty list when nothing is configured."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_jira_project_keys()
        assert result == []

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=" acme , proj ")
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_strips_whitespace_and_uppercases(self, _mock_state, _mock_config):
        """Should trim whitespace and uppercase keys."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_jira_project_keys()
        assert result == ["ACME", "PROJ"]

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=",,,")
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_ignores_empty_segments(self, _mock_state, _mock_config):
        """Should filter out empty segments from comma-separated string."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_jira_project_keys()
        assert result == []
