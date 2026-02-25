"""Tests for find_pr_from_jira_issue function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.helpers import find_pr_from_jira_issue


class TestFindPrFromJiraIssue:
    """Tests for find_pr_from_jira_issue function."""

    def test_returns_pr_id_when_found_in_ado(self, mock_azure_devops_env):
        """Should return PR ID when issue key is found in Azure DevOps."""
        pr_data = {"pullRequestId": 42, "sourceRefName": "refs/heads/feature/DFLY-1234"}

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_pull_request_by_issue_key",
            return_value=pr_data,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.review_jira.get_pr_from_development_panel",
                return_value=None,
            ):
                result = find_pr_from_jira_issue("DFLY-1234")

        assert result == 42

    def test_returns_none_when_not_found_anywhere(self, mock_azure_devops_env):
        """Should return None when no PR is found in any source."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_pull_request_by_issue_key",
            return_value=None,
        ):
            result = find_pr_from_jira_issue("DFLY-9999")

        assert result is None

    def test_handles_dev_panel_exception_gracefully(self, mock_azure_devops_env):
        """Should fall through to ADO search when dev panel lookup raises an exception."""
        pr_data = {"pullRequestId": 55}

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_pull_request_by_issue_key",
            return_value=pr_data,
        ):
            # Even if dev panel raises, ADO search should still work
            result = find_pr_from_jira_issue("DFLY-1234")

        assert result == 55
