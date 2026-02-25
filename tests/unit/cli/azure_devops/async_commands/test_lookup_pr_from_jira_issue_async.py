"""Tests for lookup_pr_from_jira_issue_async function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import lookup_pr_from_jira_issue_async


class TestLookupPrFromJiraIssueAsync:
    """Tests for lookup_pr_from_jira_issue_async function."""

    def test_saves_pull_request_id_to_state_when_found(self, capsys):
        """Should save pull_request_id to state when a PR is found for the issue."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue",
            return_value=12345,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.async_commands.get_value",
                return_value=None,
            ):
                with patch(
                    "agentic_devtools.cli.azure_devops.async_commands.set_value"
                ) as mock_set:
                    lookup_pr_from_jira_issue_async(issue_key="DFLY-1234")

        mock_set.assert_called_once_with("pull_request_id", "12345")

    def test_prints_message_when_no_pr_found(self, capsys):
        """Should print a message when no PR is found for the Jira issue."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue",
            return_value=None,
        ):
            lookup_pr_from_jira_issue_async(issue_key="DFLY-9999")

        captured = capsys.readouterr()
        assert "No active PR" in captured.out

    def test_handles_exception_gracefully(self, capsys):
        """Should not raise when an exception occurs during lookup."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_pr_from_jira_issue",
            side_effect=RuntimeError("connection error"),
        ):
            lookup_pr_from_jira_issue_async(issue_key="DFLY-0001")

        captured = capsys.readouterr()
        assert "Could not" in captured.out or "⚠️" in captured.out
