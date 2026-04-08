"""Tests for _fetch_reviews_for_pr in copilot_review_status module."""

import json
import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.copilot_review_status import _fetch_reviews_for_pr

MODULE = "agentic_devtools.cli.github.copilot_review_status"


def _ok(stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "not found") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class TestFetchReviewsForPr:
    """Tests for _fetch_reviews_for_pr."""

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_successful_paginated_response(self, mock_run, mock_sleep):
        """Successful paginated response returns all review objects."""
        reviews = [
            {"id": 1, "state": "APPROVED"},
            {"id": 2, "state": "COMMENTED"},
        ]
        # gh --jq '.[]' outputs one JSON object per line
        stdout = "\n".join(json.dumps(r) for r in reviews)
        mock_run.return_value = _ok(stdout)

        result = _fetch_reviews_for_pr(42, "owner/repo")

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        mock_sleep.assert_not_called()

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_empty_response(self, mock_run, mock_sleep):
        """Empty response (no reviews) returns empty list."""
        mock_run.return_value = _ok("")

        result = _fetch_reviews_for_pr(42, "owner/repo")

        assert result == []

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_retry_then_success(self, mock_run, mock_sleep):
        """Retries on failure and succeeds on second attempt."""
        review = {"id": 1, "state": "APPROVED"}
        mock_run.side_effect = [
            _fail("server error"),
            _ok(json.dumps(review)),
        ]

        result = _fetch_reviews_for_pr(42, "owner/repo")

        assert len(result) == 1
        assert result[0]["id"] == 1
        mock_sleep.assert_called_once_with(10)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_all_retries_exhausted_raises(self, mock_run, mock_sleep):
        """All retries exhausted raises RuntimeError."""
        mock_run.return_value = _fail("persistent error")

        with pytest.raises(RuntimeError, match="Failed to fetch reviews"):
            _fetch_reviews_for_pr(42, "owner/repo")

        assert mock_sleep.call_count == 2  # 2 retry delays

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_shell_false_passed(self, mock_run, mock_sleep):
        """run_safe is called with shell=False."""
        mock_run.return_value = _ok("")

        _fetch_reviews_for_pr(42, "owner/repo")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["shell"] is False

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe", side_effect=OSError("gh not found"))
    def test_oserror_raises_runtime_error(self, mock_run, mock_sleep):
        """OSError from run_safe (gh not installed) raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Failed to fetch reviews"):
            _fetch_reviews_for_pr(42, "owner/repo")

        assert mock_sleep.call_count == 2

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_invalid_json_raises_runtime_error(self, mock_run, mock_sleep):
        """Invalid JSON in response raises RuntimeError."""
        mock_run.return_value = _ok("not valid json")

        with pytest.raises(RuntimeError, match="Failed to parse review JSON"):
            _fetch_reviews_for_pr(42, "owner/repo")
