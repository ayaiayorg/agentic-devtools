"""Tests for release_lock."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.evaluator.lock import _LOCK_MARKER, release_lock


class TestReleaseLock:
    """Tests for release_lock function."""

    def test_release_with_matching_token(self):
        """Releases lock when token matches."""
        provider = MagicMock()
        body = f"{_LOCK_MARKER}\ntoken=my-run\nacquired=1000\nstate=active"
        provider.find_comment.return_value = (99, body)

        release_lock(provider, pr_number=42, token="my-run")

        provider.update_comment.assert_called_once()
        new_body = provider.update_comment.call_args[0][1]
        assert "state=released" in new_body

    def test_release_with_wrong_token(self):
        """Does not release when token doesn't match."""
        provider = MagicMock()
        body = f"{_LOCK_MARKER}\ntoken=other-run\nacquired=1000\nstate=active"
        provider.find_comment.return_value = (99, body)

        release_lock(provider, pr_number=42, token="my-run")

        provider.update_comment.assert_not_called()

    def test_release_no_lock_comment(self):
        """No-op when lock comment doesn't exist."""
        provider = MagicMock()
        provider.find_comment.return_value = None

        release_lock(provider, pr_number=42, token="my-run")

        provider.update_comment.assert_not_called()
