"""Tests for find_jira_issue_from_pr function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.helpers import find_jira_issue_from_pr


class TestFindJiraIssueFromPr:
    """Tests for find_jira_issue_from_pr function."""

    def test_returns_issue_key_from_branch_name(self, mock_azure_devops_env):
        """Should extract Jira issue key from the source branch name."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/PROJECT-1234/my-feature",
            "title": "Some PR",
            "description": "",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result == "PROJECT-1234"

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

    def test_returns_issue_key_from_title(self, mock_azure_devops_env):
        """Should extract Jira issue key from the PR title when branch has no key."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-issue-key",
            "title": "PROJECT-5678: fix the bug",
            "description": "",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result == "PROJECT-5678"

    def test_returns_issue_key_from_title_when_branch_empty(self, mock_azure_devops_env):
        """Should extract Jira issue key from title when sourceRefName yields empty branch."""
        pr_data = {
            "sourceRefName": "",
            "title": "PROJECT-4444: add feature",
            "description": "",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result == "PROJECT-4444"

    def test_returns_issue_key_from_description_with_empty_title(self, mock_azure_devops_env):
        """Should extract Jira issue key from description when branch and title are empty."""
        pr_data = {
            "sourceRefName": "",
            "title": "",
            "description": "Related to PROJECT-3333",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result == "PROJECT-3333"

    def test_returns_issue_key_from_description(self, mock_azure_devops_env):
        """Should extract Jira issue key from the PR description when branch and title have no key."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-issue-key",
            "title": "Fix the bug",
            "description": "Fixes PROJECT-9012 by updating the logic",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result == "PROJECT-9012"

    def test_returns_none_when_no_match_and_description_empty(self, mock_azure_devops_env):
        """Should return None when branch and title have no match and description is empty."""
        pr_data = {
            "sourceRefName": "refs/heads/feature/no-issue-key",
            "title": "Fix something",
            "description": "",
        }

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.get_pull_request_details",
            return_value=pr_data,
        ):
            result = find_jira_issue_from_pr(pull_request_id=42)

        assert result is None
