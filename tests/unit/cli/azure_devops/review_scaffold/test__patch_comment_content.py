"""Tests for _patch_comment_content helper function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.review_scaffold import _patch_comment_content


class TestPatchCommentContent:
    """Tests for _patch_comment_content helper."""

    def test_patches_correct_url(self):
        """PATCHes {threads_url}/{thread_id}/comments/{comment_id}."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        requests_mock = MagicMock()
        requests_mock.patch.return_value = resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 10, 5, "new content")

        url = requests_mock.patch.call_args[0][0]
        assert url == "https://api/threads/10/comments/5"

    def test_sends_content_in_body(self):
        """Sends the new content in the request body."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        requests_mock = MagicMock()
        requests_mock.patch.return_value = resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 1, 2, "updated text")

        body = requests_mock.patch.call_args[1]["json"]
        assert body == {"content": "updated text"}

    def test_calls_raise_for_status(self):
        """Calls raise_for_status on the response."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        requests_mock = MagicMock()
        requests_mock.patch.return_value = resp

        _patch_comment_content(requests_mock, {}, "https://api/threads", 1, 2, "content")

        resp.raise_for_status.assert_called_once()

    def test_passes_headers_and_timeout(self):
        """Passes auth headers and timeout to the request."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        requests_mock = MagicMock()
        requests_mock.patch.return_value = resp
        headers = {"Authorization": "Bearer xyz"}

        _patch_comment_content(requests_mock, headers, "https://api/threads", 1, 2, "x")

        assert requests_mock.patch.call_args[1]["headers"] == headers
        assert requests_mock.patch.call_args[1]["timeout"] == 30
