"""Tests for _demote_main_comment helper function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.review_scaffold import _demote_main_comment


class TestDemoteMainComment:
    """Tests for _demote_main_comment helper."""

    def _setup_mocks(self, old_content="Previous content", reply_id=99):
        """Build requests mock with GET→POST→PATCH configured."""
        requests_mock = MagicMock()

        # GET returns the thread with the old main comment
        get_resp = MagicMock()
        get_resp.raise_for_status = MagicMock()
        get_resp.json.return_value = {"comments": [{"id": 1, "content": old_content}]}
        requests_mock.get.return_value = get_resp

        # POST returns the new reply comment ID
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": reply_id}
        requests_mock.post.return_value = post_resp

        # PATCH succeeds
        patch_resp = MagicMock()
        patch_resp.raise_for_status = MagicMock()
        requests_mock.patch.return_value = patch_resp

        return requests_mock

    def test_returns_reply_comment_id(self):
        """Returns the comment ID of the newly-created reply."""
        requests_mock = self._setup_mocks(reply_id=42)

        result = _demote_main_comment(
            requests_mock,
            {},
            "https://api/threads",
            10,
            1,
            "New main content",
        )

        assert result == 42

    def test_gets_thread_to_read_main_comment(self):
        """Step 1: GETs the thread to read the current main comment."""
        requests_mock = self._setup_mocks()

        _demote_main_comment(requests_mock, {}, "https://api/threads", 10, 1, "New content")

        requests_mock.get.assert_called_once()
        url = requests_mock.get.call_args[0][0]
        assert url == "https://api/threads/10"

    def test_posts_old_content_as_reply(self):
        """Step 2: Posts the old main comment content as a reply."""
        requests_mock = self._setup_mocks(old_content="Old review text")

        _demote_main_comment(requests_mock, {}, "https://api/threads", 10, 1, "New content")

        post_call = requests_mock.post.call_args
        assert post_call[0][0] == "https://api/threads/10/comments"
        assert post_call[1]["json"]["content"] == "Old review text"

    def test_patches_main_with_new_content(self):
        """Step 3: PATCHes the main comment with new content."""
        requests_mock = self._setup_mocks()

        _demote_main_comment(requests_mock, {}, "https://api/threads", 10, 1, "Fresh content")

        patch_call = requests_mock.patch.call_args
        assert patch_call[0][0] == "https://api/threads/10/comments/1"
        assert patch_call[1]["json"]["content"] == "Fresh content"

    def test_sequence_is_get_post_patch(self):
        """Calls are made in order: GET, POST, PATCH."""
        requests_mock = self._setup_mocks()
        call_order = []

        def _get(*a, **kw):
            call_order.append("GET")
            return self._setup_mocks().get(*a, **kw)

        def _post(*a, **kw):
            call_order.append("POST")
            return self._setup_mocks().post(*a, **kw)

        def _patch(*a, **kw):
            call_order.append("PATCH")
            return self._setup_mocks().patch(*a, **kw)

        requests_mock.get.side_effect = _get
        requests_mock.post.side_effect = _post
        requests_mock.patch.side_effect = _patch

        _demote_main_comment(requests_mock, {}, "https://api/threads", 10, 1, "New")

        assert call_order == ["GET", "POST", "PATCH"]

    def test_handles_missing_comment_id_gracefully(self):
        """Uses empty string when the target comment ID is not found in thread."""
        requests_mock = MagicMock()
        get_resp = MagicMock()
        get_resp.raise_for_status = MagicMock()
        get_resp.json.return_value = {"comments": [{"id": 999, "content": "Other comment"}]}
        requests_mock.get.return_value = get_resp

        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 50}
        requests_mock.post.return_value = post_resp

        patch_resp = MagicMock()
        patch_resp.raise_for_status = MagicMock()
        requests_mock.patch.return_value = patch_resp

        result = _demote_main_comment(requests_mock, {}, "https://api/threads", 10, 1, "New")

        # Should still work, posting empty string as old content
        assert result == 50
        post_body = requests_mock.post.call_args[1]["json"]
        assert post_body["content"] == ""
