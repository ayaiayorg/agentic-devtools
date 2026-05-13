"""Tests for _check_reviewer_in_reviews fallback helper."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.request_copilot_review import (
    COPILOT_REVIEWER_LOGIN,
    _check_reviewer_in_reviews,
)

MODULE = "agentic_devtools.cli.github.request_copilot_review"


class TestCheckReviewerInReviews:
    """Tests for _check_reviewer_in_reviews."""

    @patch(f"{MODULE}.run_safe")
    def test_bot_found_returns_true(self, mock_run):
        """Returns True when bot has submitted a review."""
        reviews = [{"user": {"login": COPILOT_REVIEWER_LOGIN}, "state": "COMMENTED"}]
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(reviews), stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is True

    @patch(f"{MODULE}.run_safe")
    def test_bot_not_in_reviews_returns_false(self, mock_run):
        """Returns False when bot has no reviews."""
        reviews = [{"user": {"login": "other-user"}, "state": "APPROVED"}]
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(reviews), stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is False

    @patch(f"{MODULE}.run_safe")
    def test_empty_reviews_returns_false(self, mock_run):
        """Returns False when reviews list is empty."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is False

    @patch(f"{MODULE}.run_safe")
    def test_api_failure_returns_false(self, mock_run, capsys):
        """Returns False on API failure and prints warning."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not Found")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is False
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch(f"{MODULE}.run_safe")
    def test_invalid_json_returns_false(self, mock_run, capsys):
        """Returns False on JSON parse error and prints warning."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is False
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch(f"{MODULE}.run_safe")
    def test_non_list_response_returns_false(self, mock_run):
        """Returns False when response is not a list."""
        mock_run.return_value = MagicMock(returncode=0, stdout='{"data": []}', stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is False

    @patch(f"{MODULE}.run_safe")
    def test_case_insensitive_match(self, mock_run):
        """Returns True for case-insensitive login match."""
        reviews = [{"user": {"login": "Copilot-Pull-Request-Reviewer[bot]"}}]
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(reviews), stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is True

    @patch(f"{MODULE}.run_safe")
    def test_missing_user_field_skipped(self, mock_run):
        """Reviews without user field are safely skipped."""
        reviews = [{"state": "APPROVED"}, {"user": {"login": COPILOT_REVIEWER_LOGIN}}]
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(reviews), stderr="")
        assert _check_reviewer_in_reviews(42, "owner", "repo") is True

    @patch(f"{MODULE}.run_safe")
    def test_calls_reviews_api_endpoint(self, mock_run):
        """run_safe is called with the reviews API endpoint."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        _check_reviewer_in_reviews(99, "myowner", "myrepo")
        mock_run.assert_called_once_with(
            [
                "gh",
                "api",
                "repos/myowner/myrepo/pulls/99/reviews",
            ],
            capture_output=True,
            text=True,
            shell=False,
        )
