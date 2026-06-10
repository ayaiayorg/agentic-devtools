"""Tests for _reply_and_resolve_comments."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.apply_thread_autofix import _reply_and_resolve_comments

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestReplyAndResolveComments:
    """Tests for _reply_and_resolve_comments."""

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}._resolve_thread_for_comment")
    @patch(f"{_MODULE}._post_reply_to_comment")
    def test_successful_reply_and_resolve(
        self, mock_reply: MagicMock, mock_resolve: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_reply.return_value = True
        mock_resolve.return_value = True

        suggestions = [{"comment_id": 10}, {"comment_id": 20}]
        result = _reply_and_resolve_comments("owner/repo", 5, suggestions, "abc123def456789")

        assert result["replied"] == 2
        assert result["resolved"] == 2
        assert result["failed_replies"] == []
        assert result["failed_resolves"] == []

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}._resolve_thread_for_comment")
    @patch(f"{_MODULE}._post_reply_to_comment")
    def test_failed_reply_tracked(self, mock_reply: MagicMock, mock_resolve: MagicMock, mock_sleep: MagicMock) -> None:
        mock_reply.return_value = False
        mock_resolve.return_value = True

        suggestions = [{"comment_id": 10}]
        result = _reply_and_resolve_comments("owner/repo", 5, suggestions, "sha123")

        assert result["replied"] == 0
        assert result["resolved"] == 1
        assert result["failed_replies"] == [10]

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}._resolve_thread_for_comment")
    @patch(f"{_MODULE}._post_reply_to_comment")
    def test_failed_resolve_tracked(
        self, mock_reply: MagicMock, mock_resolve: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_reply.return_value = True
        mock_resolve.return_value = False

        suggestions = [{"comment_id": 30}]
        result = _reply_and_resolve_comments("owner/repo", 5, suggestions, "sha456")

        assert result["replied"] == 1
        assert result["resolved"] == 0
        assert result["failed_resolves"] == [30]
