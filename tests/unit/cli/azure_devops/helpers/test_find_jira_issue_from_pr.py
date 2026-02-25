"""Tests for find_jira_issue_from_pr function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.helpers import find_jira_issue_from_pr


class TestFindJiraIssueFromPr:
    """Tests for find_jira_issue_from_pr function."""

    def test_returns_issue_key_from_branch_name(self, mock_azure_devops_env):
        """Should extract Jira issue key from the source branch name."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/DFLY-1234/my-feature",
            "title": "Some PR",
            "description": "",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result == "DFLY-1234"

    def test_returns_none_when_no_issue_key_found(self, mock_azure_devops_env):
        """Should return None when no Jira issue key appears in PR data."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-issue",
            "title": "No issue PR",
            "description": "Nothing here.",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result is None

    def test_returns_none_when_pr_not_found(self, mock_azure_devops_env):
        """Should return None when the PR itself cannot be retrieved."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=None,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result is None
