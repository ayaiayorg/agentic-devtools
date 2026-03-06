"""Tests for _post_activity_log_entry helper function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.review_scaffold import _post_activity_log_entry


class TestPostActivityLogEntry:
    """Tests for _post_activity_log_entry."""

    def _setup_mocks(self, old_content="Previous entry", reply_id=99):
        """Build requests mock for the underlying _demote_main_comment call."""
        requests_mock = MagicMock()

        get_resp = MagicMock()
        get_resp.raise_for_status = MagicMock()
        get_resp.json.return_value = {"comments": [{"id": 1, "content": old_content}]}
        requests_mock.get.return_value = get_resp

        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": reply_id}
        requests_mock.post.return_value = post_resp

        patch_resp = MagicMock()
        patch_resp.raise_for_status = MagicMock()
        requests_mock.patch.return_value = patch_resp

        return requests_mock

    def test_delegates_to_demote_main_comment(self):
        """Calls _demote_main_comment with the correct arguments."""
        requests_mock = self._setup_mocks()

        with patch("agentic_devtools.cli.azure_devops.review_scaffold._demote_main_comment") as mock_demote:
            mock_demote.return_value = 42
            _post_activity_log_entry(
                requests_mock, {"Auth": "token"}, "https://api/threads", 10, 1, "New entry content"
            )

            mock_demote.assert_called_once_with(
                requests_mock, {"Auth": "token"}, "https://api/threads", 10, 1, "New entry content"
            )

    def test_patches_main_comment_with_new_entry(self):
        """The new entry content ends up as a PATCH on the main comment."""
        requests_mock = self._setup_mocks()

        _post_activity_log_entry(requests_mock, {}, "https://api/threads", 10, 1, "Fresh entry")

        patch_call = requests_mock.patch.call_args
        assert patch_call[1]["json"]["content"] == "Fresh entry"

    def test_posts_old_content_as_reply(self):
        """The previous main comment content is posted as a reply."""
        requests_mock = self._setup_mocks(old_content="Old log entry")

        _post_activity_log_entry(requests_mock, {}, "https://api/threads", 10, 1, "New entry")

        post_call = requests_mock.post.call_args
        assert post_call[1]["json"]["content"] == "Old log entry"

    def test_uses_correct_thread_url(self):
        """GET and POST use the thread_id in the URL."""
        requests_mock = self._setup_mocks()

        _post_activity_log_entry(requests_mock, {}, "https://api/threads", 42, 1, "Entry")

        get_url = requests_mock.get.call_args[0][0]
        assert "42" in get_url
