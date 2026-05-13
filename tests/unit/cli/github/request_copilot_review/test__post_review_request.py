"""Tests for _post_review_request helper."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.request_copilot_review import (
    COPILOT_REVIEWER_LOGIN,
    _post_review_request,
)

MODULE = "agentic_devtools.cli.github.request_copilot_review"


class TestPostReviewRequest:
    """Tests for _post_review_request."""

    @patch(f"{MODULE}.run_safe")
    def test_success_returns_true_none_false_when_no_body(self, mock_run):
        """Successful POST with empty body returns (True, None, False)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        ok, err, verified = _post_review_request(42, "owner", "repo")
        assert ok is True
        assert err is None
        assert verified is False

    @patch(f"{MODULE}.run_safe")
    def test_success_immediate_verified_from_response(self, mock_run):
        """POST response containing the bot in requested_reviewers → immediate_verified=True."""
        pr_data = {"requested_reviewers": [{"login": COPILOT_REVIEWER_LOGIN}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(pr_data), stderr="")
        ok, err, verified = _post_review_request(42, "owner", "repo")
        assert ok is True
        assert err is None
        assert verified is True

    @patch(f"{MODULE}.run_safe")
    def test_success_not_verified_when_bot_absent_from_response(self, mock_run):
        """POST response without the bot → immediate_verified=False."""
        pr_data = {"requested_reviewers": [{"login": "other-user"}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(pr_data), stderr="")
        ok, err, verified = _post_review_request(42, "owner", "repo")
        assert ok is True
        assert err is None
        assert verified is False

    @patch(f"{MODULE}.run_safe")
    def test_success_not_verified_when_invalid_json(self, mock_run):
        """POST response with invalid JSON → immediate_verified=False (non-critical)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        ok, err, verified = _post_review_request(42, "owner", "repo")
        assert ok is True
        assert err is None
        assert verified is False

    @patch(f"{MODULE}.run_safe")
    def test_success_calls_run_safe_with_correct_args(self, mock_run):
        """run_safe is called with correct arguments and shell=False."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _post_review_request(99, "myowner", "myrepo")
        mock_run.assert_called_once_with(
            [
                "gh",
                "api",
                "repos/myowner/myrepo/pulls/99/requested_reviewers",
                "-X",
                "POST",
                "-f",
                f"reviewers[]={COPILOT_REVIEWER_LOGIN}",
            ],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch(f"{MODULE}.run_safe")
    def test_failure_returns_false_with_error(self, mock_run):
        """Non-zero exit returns (False, stderr, False)."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Validation Failed")
        ok, err, verified = _post_review_request(42, "owner", "repo")
        assert ok is False
        assert err == "Validation Failed"
        assert verified is False

    @patch(f"{MODULE}.run_safe")
    def test_failure_with_empty_stderr_returns_unknown_error(self, mock_run):
        """Non-zero exit with empty stderr returns 'Unknown error'."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        ok, err, verified = _post_review_request(42, "owner", "repo")
        assert ok is False
        assert err == "Unknown error"
        assert verified is False
