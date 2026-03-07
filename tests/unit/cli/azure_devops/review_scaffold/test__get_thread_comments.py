"""Tests for _get_thread_comments helper function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.review_scaffold import _get_thread_comments


class TestGetThreadComments:
    """Tests for _get_thread_comments helper."""

    def _make_response(self, comments=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"comments": comments or []}
        return resp

    def test_returns_comments_list(self):
        """Returns the comments list from the API response."""
        comments = [{"id": 1, "content": "Hello"}, {"id": 2, "content": "World"}]
        requests_mock = MagicMock()
        requests_mock.get.return_value = self._make_response(comments)

        result = _get_thread_comments(requests_mock, {}, "https://api/threads", 10)

        assert result == comments

    def test_gets_correct_url(self):
        """GETs from {threads_url}/{thread_id}."""
        requests_mock = MagicMock()
        requests_mock.get.return_value = self._make_response()

        _get_thread_comments(requests_mock, {}, "https://api/threads", 42)

        url = requests_mock.get.call_args[0][0]
        assert url == "https://api/threads/42"

    def test_returns_empty_list_when_no_comments(self):
        """Returns empty list when response has no comments key."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {}
        requests_mock = MagicMock()
        requests_mock.get.return_value = resp

        result = _get_thread_comments(requests_mock, {}, "https://api/threads", 1)

        assert result == []

    def test_passes_headers(self):
        """Passes auth headers to the request."""
        requests_mock = MagicMock()
        requests_mock.get.return_value = self._make_response()
        headers = {"Authorization": "Bearer abc"}

        _get_thread_comments(requests_mock, headers, "https://api/threads", 1)

        assert requests_mock.get.call_args[1]["headers"] == headers
