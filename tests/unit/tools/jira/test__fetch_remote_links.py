"""Tests for agentic_devtools.tools.jira._fetch_remote_links."""

from unittest.mock import MagicMock

from agentic_devtools.tools.jira import _fetch_remote_links


class TestFetchRemoteLinks:
    """Tests for the _fetch_remote_links helper."""

    def test_returns_empty_on_exception(self):
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network error")

        result = _fetch_remote_links(
            mock_requests,
            "https://jira.example.com",
            "PROJ-1",
            {"Authorization": "Basic xxx"},
            False,
        )

        assert result == []

    def test_returns_links_on_success(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [{"object": {"title": "PR #1"}}]
        mock_requests.get.return_value = mock_response

        result = _fetch_remote_links(
            mock_requests,
            "https://jira.example.com",
            "PROJ-1",
            {"Authorization": "Basic xxx"},
            False,
        )

        assert len(result) == 1

    def test_returns_empty_for_non_list_response(self):
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_requests.get.return_value = mock_response

        result = _fetch_remote_links(
            mock_requests,
            "https://jira.example.com",
            "PROJ-1",
            {"Authorization": "Basic xxx"},
            False,
        )

        assert result == []
