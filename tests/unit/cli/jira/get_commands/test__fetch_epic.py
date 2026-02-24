"""Tests for _fetch_epic helper function."""

from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira import get_commands


class TestFetchEpic:
    """Tests for _fetch_epic helper function."""

    def test_fetch_epic_success(self, mock_jira_env):
        """Test _fetch_epic returns epic data on success."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        epic_data = {
            "key": "DFLY-100",
            "fields": {"summary": "Epic for Testing", "issuetype": {"name": "Epic"}},
        }
        mock_response.json.return_value = epic_data
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_epic(
            mock_module, "https://jira.example.com", "DFLY-100", {"Authorization": "Basic xxx"}
        )

        assert result == epic_data
        mock_module.get.assert_called_once()
        call_url = mock_module.get.call_args[0][0]
        assert "DFLY-100" in call_url
        assert "customfield_10008" in call_url

    def test_fetch_epic_returns_none_on_error(self, mock_jira_env, capsys):
        """Test _fetch_epic returns None on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_epic(
            mock_module, "https://jira.example.com", "DFLY-100", {"Authorization": "Basic xxx"}
        )

        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not fetch epic DFLY-100" in captured.err
