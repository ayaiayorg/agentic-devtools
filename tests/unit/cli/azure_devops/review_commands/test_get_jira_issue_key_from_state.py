"""Tests for get_jira_issue_key_from_state function."""


class TestGetJiraIssueKeyFromState:
    """Tests for _get_jira_issue_key_from_state function."""

    def test_returns_value_from_state(self):
        """Test returns value when set in state."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import _get_jira_issue_key_from_state

        with patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="PROJECT-1234"):
            result = _get_jira_issue_key_from_state()

        assert result == "PROJECT-1234"

    def test_returns_none_when_not_set(self):
        """Test returns None when not in state."""
        from unittest.mock import patch

        from agentic_devtools.cli.azure_devops.review_commands import _get_jira_issue_key_from_state

        with patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value=None):
            result = _get_jira_issue_key_from_state()

        assert result is None
