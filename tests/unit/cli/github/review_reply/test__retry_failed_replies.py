"""Tests for _retry_failed_replies helper."""

from unittest.mock import patch

from agentic_devtools.cli.github.review_reply import _retry_failed_replies


class TestRetryFailedReplies:
    """Tests for _retry_failed_replies."""

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_retry_succeeds_on_second_attempt(self, mock_post, mock_verify, mock_sleep):
        """Reply succeeds on first retry cycle."""
        # First retry: post succeeds
        mock_post.return_value = {"id": 77}
        # Verification finds the reply
        mock_verify.return_value = {42: True}

        failed = [{"commentId": 42, "body": "fix", "error": "post failed"}]
        succeeded, still_failed = _retry_failed_replies("owner/repo", 10, 999, failed, max_retries=2, retry_delay=0.01)

        assert len(succeeded) == 1
        assert succeeded[0]["commentId"] == 42
        assert succeeded[0]["replyId"] == 77
        assert len(still_failed) == 0

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_all_retries_exhausted(self, mock_post, mock_verify, mock_sleep):
        """Still failed after max retries."""
        mock_post.return_value = None  # Always fails
        mock_verify.return_value = {42: False}

        failed = [{"commentId": 42, "body": "fix", "error": "post failed"}]
        succeeded, still_failed = _retry_failed_replies("owner/repo", 10, 999, failed, max_retries=2, retry_delay=0.01)

        assert len(succeeded) == 0
        assert len(still_failed) == 1
        assert still_failed[0]["commentId"] == 42

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_sleep_called_between_cycles_not_before_first(self, mock_post, mock_verify, mock_sleep):
        """time.sleep() is called only between retry cycles, not before the first."""
        mock_post.return_value = None
        mock_verify.return_value = {42: False}

        failed = [{"commentId": 42, "body": "fix", "error": "post failed"}]
        _retry_failed_replies("owner/repo", 10, 999, failed, max_retries=2, retry_delay=3.0)

        # Only 1 sleep: between cycle 0 and cycle 1 (not before cycle 0)
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(3.0)

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_mixed_success_failure(self, mock_post, mock_verify, mock_sleep):
        """Some replies succeed while others fail in the same retry."""
        # First call succeeds, second fails
        mock_post.side_effect = [{"id": 77}, None]
        mock_verify.return_value = {10: True, 20: False}

        failed = [
            {"commentId": 10, "body": "a", "error": "post failed"},
            {"commentId": 20, "body": "b", "error": "post failed"},
        ]
        succeeded, still_failed = _retry_failed_replies("owner/repo", 5, 999, failed, max_retries=1, retry_delay=0.01)

        assert len(succeeded) == 1
        assert succeeded[0]["commentId"] == 10
        assert len(still_failed) == 1
        assert still_failed[0]["commentId"] == 20

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_empty_failed_entries(self, mock_post, mock_verify, mock_sleep):
        """No retries when failed_entries is empty."""
        succeeded, still_failed = _retry_failed_replies("owner/repo", 10, 999, [], max_retries=2, retry_delay=0.01)
        assert succeeded == []
        assert still_failed == []
        mock_sleep.assert_not_called()

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_verification_failure_uses_verify_only_path(self, mock_post, mock_verify, mock_sleep):
        """Entries with error='verification failed' are re-verified without re-posting."""
        # Verification succeeds on retry
        mock_verify.return_value = {42: True}

        failed = [{"commentId": 42, "body": "fix", "error": "verification failed"}]
        succeeded, still_failed = _retry_failed_replies("owner/repo", 10, 999, failed, max_retries=1, retry_delay=0.01)

        # Should NOT have called _post_single_reply for verify-only entries
        mock_post.assert_not_called()
        assert len(succeeded) == 1
        assert succeeded[0]["commentId"] == 42
        assert succeeded[0]["verified"] is True
        assert len(still_failed) == 0

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_verify_only_failure_escalates_to_repost(self, mock_post, mock_verify, mock_sleep):
        """If verify-only retry still fails, next cycle re-posts."""
        # First cycle: verify fails; second cycle: post+verify succeeds
        mock_verify.side_effect = [{42: False}, {42: True}]
        mock_post.return_value = {"id": 99}

        failed = [{"commentId": 42, "body": "fix", "error": "verification failed"}]
        succeeded, still_failed = _retry_failed_replies("owner/repo", 10, 999, failed, max_retries=2, retry_delay=0.01)

        # First cycle: no post (verify-only). Second cycle: re-posts.
        assert mock_post.call_count == 1
        assert len(succeeded) == 1
        assert succeeded[0]["commentId"] == 42

    @patch("agentic_devtools.cli.github.review_reply.time.sleep")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    def test_post_ok_but_verify_fails_does_not_repost_next_cycle(self, mock_post, mock_verify, mock_sleep):
        """When post succeeds but verification fails, the next cycle only re-verifies."""
        # Cycle 0: post succeeds, verification fails → should mark "verification failed"
        # Cycle 1: verify-only (no re-post), verification succeeds
        mock_post.return_value = {"id": 88}
        mock_verify.side_effect = [{42: False}, {42: True}]

        failed = [{"commentId": 42, "body": "fix", "error": "post failed"}]
        succeeded, still_failed = _retry_failed_replies("owner/repo", 10, 999, failed, max_retries=2, retry_delay=0.01)

        # Post called only once (cycle 0); cycle 1 is verify-only
        assert mock_post.call_count == 1
        assert len(succeeded) == 1
        assert succeeded[0]["commentId"] == 42
        assert succeeded[0]["verified"] is True
        assert len(still_failed) == 0
