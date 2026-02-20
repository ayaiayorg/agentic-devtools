"""Tests for the review_commands module and helper functions."""


class TestFetchAndDisplayJiraIssue:
    """Tests for _fetch_and_display_jira_issue function."""

    def test_returns_true_on_success(self):
        """Test returns True when Jira issue fetched successfully."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value"):
            with patch("agdt_ai_helpers.cli.jira.get_commands.get_issue") as mock_get_issue:
                with patch("agdt_ai_helpers.cli.jira.state_helpers.set_jira_value"):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        _fetch_and_display_jira_issue,
                    )

                    result = _fetch_and_display_jira_issue("DFLY-1234")
                    assert result is True
                    mock_get_issue.assert_called_once()

    def test_returns_false_on_system_exit(self, capsys):
        """Test returns False when get_issue raises SystemExit."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value"):
            with patch(
                "agdt_ai_helpers.cli.jira.get_commands.get_issue",
                side_effect=SystemExit(1),
            ):
                with patch("agdt_ai_helpers.cli.jira.state_helpers.set_jira_value"):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        _fetch_and_display_jira_issue,
                    )

                    result = _fetch_and_display_jira_issue("DFLY-1234")
                    assert result is False
                    captured = capsys.readouterr()
                    assert "could not be fetched" in captured.err

    def test_returns_false_on_exception(self, capsys):
        """Test returns False when get_issue raises Exception."""
        from unittest.mock import patch

        with patch("agdt_ai_helpers.cli.azure_devops.review_commands.get_value"):
            with patch(
                "agdt_ai_helpers.cli.jira.get_commands.get_issue",
                side_effect=Exception("API error"),
            ):
                with patch("agdt_ai_helpers.cli.jira.state_helpers.set_jira_value"):
                    from agdt_ai_helpers.cli.azure_devops.review_commands import (
                        _fetch_and_display_jira_issue,
                    )

                    result = _fetch_and_display_jira_issue("DFLY-1234")
                    assert result is False
                    captured = capsys.readouterr()
                    assert "Failed to fetch Jira issue" in captured.err
