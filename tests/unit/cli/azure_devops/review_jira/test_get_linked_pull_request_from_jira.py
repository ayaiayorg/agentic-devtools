"""
Tests for review_jira module.
"""

from unittest.mock import patch


class TestGetLinkedPullRequestFromJira:
    """Tests for get_linked_pull_request_from_jira function."""

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_jira_issue")
    def test_returns_pr_id_from_issue(self, mock_fetch):
        """Test returning PR ID from issue."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            get_linked_pull_request_from_jira,
        )

        mock_fetch.return_value = {"fields": {"comment": {"comments": [{"body": "PR #4444"}]}}}

        result = get_linked_pull_request_from_jira("DFLY-1234")
        assert result == 4444

    @patch("agentic_devtools.cli.azure_devops.review_jira.fetch_jira_issue")
    def test_returns_none_when_fetch_fails(self, mock_fetch):
        """Test returning None when fetch fails."""
        from agentic_devtools.cli.azure_devops.review_jira import (
            get_linked_pull_request_from_jira,
        )

        mock_fetch.return_value = None

        result = get_linked_pull_request_from_jira("DFLY-1234")
        assert result is None
