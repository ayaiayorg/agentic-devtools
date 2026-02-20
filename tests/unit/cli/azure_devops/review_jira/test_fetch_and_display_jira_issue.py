"""
Tests for review_jira module.
"""

from unittest.mock import patch


class TestFetchAndDisplayJiraIssue:
    """Tests for fetch_and_display_jira_issue function."""

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_jira_issue")
    @patch("agentic_devtools.cli.azure_devops.review_jira.display_jira_issue_summary")
    def test_fetches_and_displays_issue(self, mock_display, mock_fetch):
        """Test fetching and displaying issue."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_and_display_jira_issue,
        )

        mock_fetch.return_value = {"key": "DFLY-1234"}

        result = fetch_and_display_jira_issue("DFLY-1234")

        assert result == {"key": "DFLY-1234"}
        mock_display.assert_called_once_with({"key": "DFLY-1234"})

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_jira_issue")
    @patch("agentic_devtools.cli.azure_devops.review_jira.display_jira_issue_summary")
    def test_does_not_display_when_fetch_fails(self, mock_display, mock_fetch):
        """Test that display is not called when fetch fails."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            fetch_and_display_jira_issue,
        )

        mock_fetch.return_value = None

        result = fetch_and_display_jira_issue("DFLY-1234")

        assert result is None
        mock_display.assert_not_called()
