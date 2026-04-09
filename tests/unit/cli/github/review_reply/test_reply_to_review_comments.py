"""Tests for reply_to_review_comments core function."""

from unittest.mock import call, patch

from agentic_devtools.cli.github.review_reply import _MAX_RETRIES, reply_to_review_comments


class TestReplyToReviewComments:
    """Tests for reply_to_review_comments."""

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_full_success_flow(self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set):
        """All replies posted and verified successfully."""
        mock_load.return_value = [
            {"commentId": 1, "body": "done"},
            {"commentId": 2, "body": "fixed"},
        ]
        mock_post.side_effect = [{"id": 101}, {"id": 102}]
        mock_verify.return_value = {1: True, 2: True}

        result = reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        assert result["totalReplies"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert result["verified"] is True
        assert len(result["details"]) == 2
        assert len(result["failedDetails"]) == 0
        mock_retry.assert_not_called()

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_state_keys_written(self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set):
        """State keys are written correctly."""
        mock_load.return_value = [{"commentId": 1, "body": "ok"}]
        mock_post.return_value = {"id": 101}
        mock_verify.return_value = {1: True}

        reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        calls = mock_set.call_args_list
        assert call("github.review_replies_total", 1) in calls
        assert call("github.review_replies_successful", 1) in calls
        assert call("github.review_replies_failed", 0) in calls
        assert call("github.review_replies_verified", True) in calls

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_empty_replies_file(self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set):
        """Empty replies file returns zeros and verified=True."""
        mock_load.return_value = []

        result = reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        assert result["totalReplies"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
        assert result["verified"] is True
        mock_post.assert_not_called()

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_partial_failure(self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set):
        """Partial failure: one reply fails, one succeeds."""
        mock_load.return_value = [
            {"commentId": 1, "body": "ok"},
            {"commentId": 2, "body": "fail"},
        ]
        # First succeeds, second fails
        mock_post.side_effect = [{"id": 101}, None]
        mock_verify.return_value = {1: True}
        mock_retry.return_value = ([], [{"commentId": 2, "body": "fail", "error": "post failed"}])

        result = reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        assert result["totalReplies"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["verified"] is False
        assert len(result["failedDetails"]) == 1
        assert result["failedDetails"][0]["commentId"] == 2
        # retryCount must match the module constant, not be hard-coded
        assert result["failedDetails"][0]["retryCount"] == _MAX_RETRIES

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_result_structure(self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set):
        """Result dict has all required keys."""
        mock_load.return_value = [{"commentId": 1, "body": "ok"}]
        mock_post.return_value = {"id": 101}
        mock_verify.return_value = {1: True}

        result = reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        assert "prNumber" in result
        assert "repo" in result
        assert "reviewId" in result
        assert "totalReplies" in result
        assert "successful" in result
        assert "failed" in result
        assert "verified" in result
        assert "details" in result
        assert "failedDetails" in result
        assert result["prNumber"] == 10
        assert result["repo"] == "owner/repo"
        assert result["reviewId"] == 999

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_verification_failure_triggers_retry(
        self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set
    ):
        """Post succeeds but verification fails → enters retry path."""
        mock_load.return_value = [{"commentId": 1, "body": "ok"}]
        mock_post.return_value = {"id": 101}
        # Verification says unverified
        mock_verify.return_value = {1: False}
        # Retry succeeds
        mock_retry.return_value = (
            [{"commentId": 1, "status": "replied", "replyId": 101, "verified": True}],
            [],
        )

        result = reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        mock_retry.assert_called_once()
        # After retry success, detail should be updated
        assert result["details"][0]["verified"] is True
        assert result["successful"] == 1
        assert result["failed"] == 0

    @patch("agentic_devtools.cli.github.review_reply.set_value")
    @patch("agentic_devtools.cli.github.review_reply._retry_failed_replies")
    @patch("agentic_devtools.cli.github.review_reply._verify_replies")
    @patch("agentic_devtools.cli.github.review_reply._post_single_reply")
    @patch("agentic_devtools.cli.github.review_reply._validate_reply_entries")
    @patch("agentic_devtools.cli.github.review_reply._load_replies_file")
    def test_retry_preserves_reply_id_for_verify_only(
        self, mock_load, mock_validate, mock_post, mock_verify, mock_retry, mock_set
    ):
        """Retry re-verify-only path preserves original replyId when retry returns None."""
        mock_load.return_value = [{"commentId": 1, "body": "ok"}]
        mock_post.return_value = {"id": 101}
        # Verification says unverified → triggers retry
        mock_verify.return_value = {1: False}
        # Retry succeeds but returns replyId=None (re-verify-only path)
        mock_retry.return_value = (
            [{"commentId": 1, "status": "replied", "replyId": None, "verified": True}],
            [],
        )

        result = reply_to_review_comments(10, "owner/repo", 999, "replies.json")

        # The original replyId (101) should be preserved, not overwritten with None
        assert result["details"][0]["replyId"] == 101
        assert result["details"][0]["verified"] is True
