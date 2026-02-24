"""Tests for _fetch_remote_links helper function."""

from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira import get_commands


class TestFetchRemoteLinks:
    """Tests for _fetch_remote_links function."""

    def test_returns_empty_list_on_exception(self, mock_jira_env):
        """Test _fetch_remote_links returns empty list on API error."""
        mock_module = MagicMock()
        mock_module.get.side_effect = Exception("Network error")

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == []

    def test_returns_empty_list_for_non_list_response(self, mock_jira_env):
        """Test _fetch_remote_links handles non-list response."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert result == []

    def test_returns_list_of_remote_links(self, mock_jira_env):
        """Test _fetch_remote_links returns list of links."""
        mock_module = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"object": {"title": "Link 1"}},
            {"object": {"title": "Link 2"}},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_module.get.return_value = mock_response

        result = get_commands._fetch_remote_links(
            mock_module, "https://jira.example.com", "DFLY-1234", {"Authorization": "Basic xxx"}
        )

        assert len(result) == 2
