"""Tests for _post_reply_to_comment."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.apply_thread_autofix import _post_reply_to_comment

_MODULE = "agentic_devtools.cli.github.apply_thread_autofix"


class TestPostReplyToComment:
    """Tests for _post_reply_to_comment."""

    @patch(f"{_MODULE}.run_safe")
    def test_returns_true_on_success(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=0, stdout="{}", stderr="")
        result = _post_reply_to_comment("owner/repo", 5, 100, "reply body")
        assert result is True

    @patch(f"{_MODULE}.run_safe")
    def test_returns_false_on_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = _post_reply_to_comment("owner/repo", 5, 100, "reply body")
        assert result is False
