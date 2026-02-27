"""Tests for _post_thread helper."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.review_scaffold import _post_thread


def _make_post_response(thread_id: int, comment_id: int) -> MagicMock:
    """Build a mock requests.post response for thread creation."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "id": thread_id,
        "comments": [{"id": comment_id}],
    }
    return resp


class TestPostThread:
    """Tests for _post_thread helper."""

    def test_returns_thread_and_comment_id(self):
        """Returns (thread_id, comment_id) from API response."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = _make_post_response(thread_id=100, comment_id=200)

        thread_id, comment_id = _post_thread(requests_mock, {}, "https://url", "content")

        assert thread_id == 100
        assert comment_id == 200

    def test_posts_without_thread_context_when_no_file_path(self):
        """Posts thread body without threadContext when file_path is None."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = _make_post_response(1, 2)

        _post_thread(requests_mock, {}, "https://url", "content", file_path=None)

        call_kwargs = requests_mock.post.call_args[1]
        body = call_kwargs["json"]
        assert "threadContext" not in body

    def test_posts_with_file_context_when_file_path_given(self):
        """Posts thread body with threadContext.filePath when file_path is provided."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = _make_post_response(1, 2)

        _post_thread(requests_mock, {}, "https://url", "content", file_path="/src/file.ts")

        call_kwargs = requests_mock.post.call_args[1]
        body = call_kwargs["json"]
        assert body["threadContext"] == {"filePath": "/src/file.ts"}

    def test_calls_raise_for_status(self):
        """Calls raise_for_status on the response."""
        requests_mock = MagicMock()
        resp = _make_post_response(1, 2)
        requests_mock.post.return_value = resp

        _post_thread(requests_mock, {}, "https://url", "content")

        resp.raise_for_status.assert_called_once()

    def test_thread_status_is_active(self):
        """Thread body has status='active'."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = _make_post_response(1, 2)

        _post_thread(requests_mock, {}, "https://url", "content")

        body = requests_mock.post.call_args[1]["json"]
        assert body["status"] == "active"

    def test_comment_type_is_text(self):
        """Comment in thread body has commentType='text'."""
        requests_mock = MagicMock()
        requests_mock.post.return_value = _make_post_response(1, 2)

        _post_thread(requests_mock, {}, "https://url", "my comment")

        body = requests_mock.post.call_args[1]["json"]
        assert body["comments"][0]["commentType"] == "text"
        assert body["comments"][0]["content"] == "my comment"
