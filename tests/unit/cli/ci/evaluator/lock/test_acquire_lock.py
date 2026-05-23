"""Tests for acquire_lock."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.evaluator.lock import _LOCK_MARKER, acquire_lock


class TestAcquireLock:
    """Tests for acquire_lock function."""

    def test_acquire_when_no_existing_lock(self):
        """Creates a new lock comment when none exists."""
        provider = MagicMock()
        verified_body = f"{_LOCK_MARKER}\ntoken=run-1\nacquired=1000\nstate=active"
        provider.find_comment.side_effect = [None, (123, verified_body)]
        provider.post_comment.return_value = 123

        with patch("agentic_devtools.cli.ci.evaluator.lock._get_writer_token", return_value="run-1"):
            token = acquire_lock(provider, pr_number=42)

        assert token == "run-1"
        provider.post_comment.assert_called_once()
        body = provider.post_comment.call_args[0][1]
        assert _LOCK_MARKER in body
        assert "token=run-1" in body

    def test_acquire_when_lock_stale(self):
        """Takes over a stale lock (age > TTL)."""
        provider = MagicMock()
        # Lock acquired 600 seconds ago (> 300 TTL)
        old_body = f"{_LOCK_MARKER}\ntoken=old-run\nacquired=0\nstate=active"
        verified_body = f"{_LOCK_MARKER}\ntoken=new-run\nacquired=1000\nstate=active"
        provider.find_comment.side_effect = [(99, old_body), (99, verified_body)]

        with patch("agentic_devtools.cli.ci.evaluator.lock._get_writer_token", return_value="new-run"):
            token = acquire_lock(provider, pr_number=42)

        assert token == "new-run"
        provider.update_comment.assert_called_once()

    def test_acquire_fails_when_lock_held(self):
        """Returns None when lock is held by another run and not stale."""
        provider = MagicMock()
        import time

        recent_time = str(int(time.time()))
        body = f"{_LOCK_MARKER}\ntoken=other-run\nacquired={recent_time}\nstate=active"
        provider.find_comment.return_value = (99, body)

        with patch("agentic_devtools.cli.ci.evaluator.lock._get_writer_token", return_value="my-run"):
            token = acquire_lock(provider, pr_number=42)

        assert token is None
        provider.update_comment.assert_not_called()
        provider.post_comment.assert_not_called()

    def test_acquire_same_token_succeeds(self):
        """Re-acquiring with the same token succeeds (idempotent)."""
        provider = MagicMock()
        import time

        recent_time = str(int(time.time()))
        body = f"{_LOCK_MARKER}\ntoken=my-run\nacquired={recent_time}\nstate=active"
        provider.find_comment.side_effect = [(99, body), (99, body)]

        with patch("agentic_devtools.cli.ci.evaluator.lock._get_writer_token", return_value="my-run"):
            token = acquire_lock(provider, pr_number=42)

        assert token == "my-run"
        provider.update_comment.assert_called_once()

    def test_acquire_returns_none_when_verification_shows_different_owner(self):
        """Returns None when post-acquire verification does not confirm ownership."""
        provider = MagicMock()
        verification_body = f"{_LOCK_MARKER}\ntoken=other-run\nacquired=1000\nstate=active"
        provider.find_comment.side_effect = [None, (124, verification_body)]

        with patch("agentic_devtools.cli.ci.evaluator.lock._get_writer_token", return_value="my-run"):
            token = acquire_lock(provider, pr_number=42)

        assert token is None
        provider.post_comment.assert_called_once()

    def test_acquire_returns_none_when_verification_comment_missing(self):
        """Returns None when verification cannot find a canonical lock comment."""
        provider = MagicMock()
        provider.find_comment.side_effect = [None, None]

        with patch("agentic_devtools.cli.ci.evaluator.lock._get_writer_token", return_value="my-run"):
            token = acquire_lock(provider, pr_number=42)

        assert token is None
        provider.post_comment.assert_called_once()
