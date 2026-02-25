"""Tests for lookup_jira_issue_from_pr_async function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import lookup_jira_issue_from_pr_async


class TestLookupJiraIssueFromPrAsync:
    """Tests for lookup_jira_issue_from_pr_async function."""

    def test_saves_issue_key_to_state_when_found(self, capsys):
        """Should save jira.issue_key to state when a Jira issue is found in the PR."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr",
            return_value="DFLY-1234",
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.async_commands.get_value",
                return_value=None,
            ):
                with patch(
                    "agentic_devtools.cli.azure_devops.async_commands.set_value"
                ) as mock_set:
                    lookup_jira_issue_from_pr_async(pull_request_id=42)

        mock_set.assert_called_once_with("jira.issue_key", "DFLY-1234")

    def test_prints_message_when_no_issue_found(self, capsys):
        """Should print a message when no Jira issue key is found in the PR."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr",
            return_value=None,
        ):
            lookup_jira_issue_from_pr_async(pull_request_id=99)

        captured = capsys.readouterr()
        assert "No Jira issue" in captured.out

    def test_handles_exception_gracefully(self, capsys):
        """Should not raise when an exception occurs during lookup."""
        with patch(
            "agentic_devtools.cli.azure_devops.helpers.find_jira_issue_from_pr",
            side_effect=RuntimeError("network error"),
        ):
            lookup_jira_issue_from_pr_async(pull_request_id=1)

        captured = capsys.readouterr()
        assert "Could not" in captured.out or "⚠️" in captured.out
