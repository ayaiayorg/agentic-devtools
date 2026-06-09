"""Tests for _patch_comment_content 403 fallback to reply."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.review_scaffold import _patch_comment_content


class TestPatchContentFallback:
    """Tests for _patch_comment_content cross-identity fallback."""

    def test_normal_patch_succeeds(self):
        """Normal PATCH (no 403) works as before."""
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        requests_mock = MagicMock()
        requests_mock.patch.return_value = resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 10, 5, "new content")

        requests_mock.patch.assert_called_once()
        requests_mock.post.assert_not_called()

    def test_403_falls_back_to_reply(self):
        """403 on PATCH should fall back to posting a reply."""
        patch_resp = MagicMock()
        patch_resp.status_code = 403
        patch_resp.raise_for_status.side_effect = Exception("403")

        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 99}

        requests_mock = MagicMock()
        requests_mock.patch.return_value = patch_resp
        requests_mock.post.return_value = post_resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 10, 5, "new content")

        # PATCH was attempted
        requests_mock.patch.assert_called_once()
        # Reply was posted
        requests_mock.post.assert_called_once()
        post_body = requests_mock.post.call_args[1]["json"]
        assert "cross-identity-update" in post_body["content"]
        assert "new content" in post_body["content"]

    def test_cross_identity_true_skips_patch(self):
        """cross_identity=True should skip PATCH and go directly to reply."""
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 99}

        requests_mock = MagicMock()
        requests_mock.post.return_value = post_resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 10, 5, "new content", cross_identity=True)

        # PATCH was NOT attempted
        requests_mock.patch.assert_not_called()
        # Reply was posted
        requests_mock.post.assert_called_once()
        post_body = requests_mock.post.call_args[1]["json"]
        assert "cross-identity-update" in post_body["content"]

    def test_reply_url_uses_correct_thread(self):
        """The reply should be posted to the correct thread URL."""
        post_resp = MagicMock()
        post_resp.raise_for_status = MagicMock()
        post_resp.json.return_value = {"id": 99}

        requests_mock = MagicMock()
        requests_mock.post.return_value = post_resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 42, 1, "content", cross_identity=True)

        post_url = requests_mock.post.call_args[0][0]
        assert "/42/comments" in post_url
