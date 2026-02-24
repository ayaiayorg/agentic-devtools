"""Tests for _fetch_parent_issue helper function."""

from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira import get_commands


class TestFetchParentIssue:
    """Tests for _fetch_parent_issue helper function."""

    def test_fetch_parent_issue_success(self, mock_jira_env):
        """Test _fetch_parent_issue returns parent data on success."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        parent_data = {
            "key": "DFLY-1234",
            "fields": {"summary": "Parent Issue"},
        }
        mock_response.json.return_value = parent_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_parent_issue(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == parent_data

    def test_fetch_parent_issue_returns_none_on_error(self, mock_jira_env, capsys):
        """Test _fetch_parent_issue returns None on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_parent_issue(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not fetch parent issue DFLY-1234" in captured.err
