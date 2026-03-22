"""Tests for get_jira_credentials function."""

import os
from unittest.mock import patch


class TestGetJiraCredentials:
    """Tests for get_jira_credentials function."""

    def test_returns_pat_from_environment(self):
        """Test that PAT is returned from environment variable."""
        from agentic_devtools.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {"JIRA_COPILOT_PAT": "test-token"}):
            pat, base_url = get_jira_credentials()
            assert pat == "test-token"

    def test_returns_none_when_pat_not_set(self):
        """Test that None is returned when PAT is not set."""
        from agentic_devtools.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {}, clear=True):
            pat, base_url = get_jira_credentials()
            assert pat is None

    def test_returns_default_base_url(self):
        """Test that empty base URL is returned when Jira is unconfigured."""
        from agentic_devtools.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "agentic_devtools.cli.jira.config.get_jira_base_url",
                side_effect=ValueError("not configured"),
            ):
                pat, base_url = get_jira_credentials()
                assert base_url == ""

    def test_returns_base_url_from_config(self):
        """Test that base URL from config cascade is returned."""
        from agentic_devtools.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "agentic_devtools.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com",
            ):
                pat, base_url = get_jira_credentials()
                assert base_url == "https://jira.example.com"

    def test_returns_custom_base_url(self):
        """Test that custom base URL from env is returned via config cascade."""
        from agentic_devtools.cli.azure_devops.review_jira import get_jira_credentials

        with patch.dict(os.environ, {"JIRA_BASE_URL": "https://jira.example.com/"}):
            with patch(
                "agentic_devtools.cli.jira.config.get_jira_base_url",
                return_value="https://jira.example.com/",
            ):
                pat, base_url = get_jira_credentials()
                assert base_url == "https://jira.example.com"
