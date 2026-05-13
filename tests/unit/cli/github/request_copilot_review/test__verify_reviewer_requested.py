"""Tests for _verify_reviewer_requested helper."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.github.request_copilot_review import (
    COPILOT_REVIEWER_LOGIN,
    _verify_reviewer_requested,
)

MODULE = "agentic_devtools.cli.github.request_copilot_review"


class TestVerifyReviewerRequested:
    """Tests for _verify_reviewer_requested."""

    @patch(f"{MODULE}.run_safe")
    def test_bot_found_returns_true(self, mock_run):
        """Returns True when bot login is in users array."""
        data = {"users": [{"login": COPILOT_REVIEWER_LOGIN}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is True

    @patch(f"{MODULE}.run_safe")
    def test_bot_not_in_users_returns_false(self, mock_run):
        """Returns False when bot login is not in users array."""
        data = {"users": [{"login": "other-user"}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is False

    @patch(f"{MODULE}.run_safe")
    def test_case_insensitive_match(self, mock_run):
        """Returns True for case-insensitive login match."""
        data = {"users": [{"login": "Copilot-Pull-Request-Reviewer[bot]"}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is True

    @patch(f"{MODULE}.run_safe")
    def test_empty_users_array_returns_false(self, mock_run):
        """Returns False when users array is empty."""
        data = {"users": []}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is False

    @patch(f"{MODULE}.run_safe")
    def test_missing_users_key_returns_false(self, mock_run):
        """Returns False when 'users' key is missing from response."""
        data = {"teams": []}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is False

    @patch(f"{MODULE}.run_safe")
    def test_api_failure_returns_false(self, mock_run, capsys):
        """Returns False on API failure and prints warning."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not Found")
        assert _verify_reviewer_requested(42, "owner", "repo") is False
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch(f"{MODULE}.run_safe")
    def test_json_parse_error_returns_false(self, mock_run, capsys):
        """Returns False on JSON parse error and prints warning."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not valid json", stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is False
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch(f"{MODULE}.run_safe")
    def test_calls_run_safe_with_correct_args(self, mock_run):
        """run_safe is called with correct GET arguments and shell=False."""
        data = {"users": []}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        _verify_reviewer_requested(99, "myowner", "myrepo")
        mock_run.assert_called_once_with(
            [
                "gh",
                "api",
                "repos/myowner/myrepo/pulls/99/requested_reviewers",
            ],
            capture_output=True,
            text=True,
            shell=False,
        )

    @patch(f"{MODULE}.run_safe")
    def test_bot_found_in_teams_slug_returns_true(self, mock_run):
        """Returns True when bot slug appears in teams array."""
        data = {"users": [], "teams": [{"slug": COPILOT_REVIEWER_LOGIN}]}
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(data), stderr="")
        assert _verify_reviewer_requested(42, "owner", "repo") is True
