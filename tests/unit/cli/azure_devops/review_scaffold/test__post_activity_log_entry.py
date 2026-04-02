"""Tests for _post_activity_log_entry helper function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.review_scaffold import _post_activity_log_entry


class TestPostActivityLogEntry:
    """Tests for _post_activity_log_entry."""

    def _setup_mocks(self, reply_id=99):
        """Build requests mock for the underlying _post_reply call."""
        requests_mock = MagicMock()

        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": reply_id}
        requests_mock.post.return_value = post_resp

        return requests_mock

    def test_delegates_to_post_reply(self):
        """Calls _post_reply with the correct arguments."""
        requests_mock = self._setup_mocks()

        with patch("agentic_devtools.cli.azure_devops.review_scaffold._post_reply") as mock_reply:
            mock_reply.return_value = 42
            result = _post_activity_log_entry(
                requests_mock, {"Auth": "token"}, "https://api/threads", 10, "New entry content"
            )

            mock_reply.assert_called_once_with(
                requests_mock, {"Auth": "token"}, "https://api/threads", 10, "New entry content"
            )
            assert result == 42

    def test_returns_comment_id(self):
        """Returns the comment ID from the reply."""
        requests_mock = self._setup_mocks(reply_id=77)

        result = _post_activity_log_entry(requests_mock, {}, "https://api/threads", 10, "Entry content")

        assert result == 77

    def test_posts_entry_as_reply(self):
        """The entry content is posted as a reply (not as a PATCH on the main comment)."""
        requests_mock = self._setup_mocks()

        _post_activity_log_entry(requests_mock, {}, "https://api/threads", 10, "Fresh entry")

        post_call = requests_mock.post.call_args
        assert post_call[1]["json"]["content"] == "Fresh entry"
        # No GET or PATCH calls — replies don't read or modify the main comment
        requests_mock.get.assert_not_called()
        requests_mock.patch.assert_not_called()

    def test_uses_correct_thread_url(self):
        """POST uses the thread_id in the URL."""
        requests_mock = self._setup_mocks()

        _post_activity_log_entry(requests_mock, {}, "https://api/threads", 42, "Entry")

        post_url = requests_mock.post.call_args[0][0]
        assert "42" in post_url

    def test_urls_correct_when_threads_url_has_query_string(self):
        """POST uses the thread_id as path segment before query string."""
        requests_mock = self._setup_mocks()

        _post_activity_log_entry(requests_mock, {}, "https://api/threads?api-version=7.0", 42, "Entry")

        post_url = requests_mock.post.call_args[0][0]
        assert post_url == "https://api/threads/42/comments?api-version=7.0"
