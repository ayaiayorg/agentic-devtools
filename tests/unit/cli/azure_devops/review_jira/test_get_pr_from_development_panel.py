"""
Tests for review_jira module.
"""

from unittest.mock import patch


class TestGetPrFromDevelopmentPanel:
    """Tests for get_pr_from_development_panel function."""

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_development_panel_prs")
    def test_returns_pr_id_from_development_panel(self, mock_fetch):
        """Test returning PR ID from development panel."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            get_pr_from_development_panel,
        )

        mock_fetch.return_value = [{"url": "https://dev.azure.com/org/project/_git/repo/pullrequest/7777"}]

        result = get_pr_from_development_panel("DFLY-1234")
        assert result == 7777
        mock_fetch.assert_called_once_with("DFLY-1234", False)

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_development_panel_prs")
    def test_returns_none_when_no_prs(self, mock_fetch):
        """Test returning None when no PRs in development panel."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            get_pr_from_development_panel,
        )

        mock_fetch.return_value = []

        result = get_pr_from_development_panel("DFLY-1234")
        assert result is None

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_development_panel_prs")
    def test_passes_verbose_flag(self, mock_fetch):
        """Test that verbose flag is passed through."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            get_pr_from_development_panel,
        )

        mock_fetch.return_value = []

        get_pr_from_development_panel("DFLY-1234", verbose=True)
        mock_fetch.assert_called_once_with("DFLY-1234", True)
