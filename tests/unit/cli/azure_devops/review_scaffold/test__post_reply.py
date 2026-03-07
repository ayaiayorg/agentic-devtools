"""Tests for _post_reply helper function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.review_scaffold import _post_reply


class TestPostReply:
    """Tests for _post_reply helper."""

    def _make_response(self, comment_id=42):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"id": comment_id}
        return resp

    def test_returns_comment_id(self):
        """Returns the comment ID from the API response."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = self._make_response(comment_id=99)

        result = _post_reply(requests_mock, {"Authorization": "Bearer x"}, "https://api/threads", 10, "Hello")

        assert result == 99

    def test_posts_to_correct_url(self):
        """Posts to {threads_url}/{thread_id}/comments."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = self._make_response()

        _post_reply(requests_mock, {}, "https://api/threads", 42, "content")

        url = requests_mock.post.call_args[0][0]
        assert url == "https://api/threads/42/comments"

    def test_sends_correct_body(self):
        """Sends content and commentType in the request body."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = self._make_response()

        _post_reply(requests_mock, {}, "https://api/threads", 1, "My reply")

        body = requests_mock.post.call_args[1]["json"]
        assert body == {"content": "My reply", "commentType": "text"}

    def test_passes_headers(self):
        """Passes auth headers to the request."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = self._make_response()
        headers = {"Authorization": "Bearer token123"}

        _post_reply(requests_mock, headers, "https://api/threads", 1, "content")

        assert requests_mock.post.call_args[1]["headers"] == headers

    def test_calls_raise_for_status(self):
        """Calls raise_for_status on the response."""
        resp = self._make_response()
        requests_mock = MagicMock()
        requests_mock.post.return_value = resp

        _post_reply(requests_mock, {}, "https://api/threads", 1, "content")

        resp.raise_for_status.assert_called_once()

    def test_uses_timeout(self):
        """Uses a timeout for the API call."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = self._make_response()

        _post_reply(requests_mock, {}, "https://api/threads", 1, "content")

        assert requests_mock.post.call_args[1]["timeout"] == 30
