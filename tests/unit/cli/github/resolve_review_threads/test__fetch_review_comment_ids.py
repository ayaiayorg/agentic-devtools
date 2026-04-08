"""Tests for _fetch_review_comment_ids helper."""

import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.resolve_review_threads import (
    _fetch_review_comment_ids,
)

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"


class TestFetchReviewCommentIds:
    """Tests for _fetch_review_comment_ids."""

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_successful_fetch(self, mock_run, mock_sleep):
        """Return parsed integer IDs on success."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="111\n222\n333\n", stderr="")
        result = _fetch_review_comment_ids(42, "owner/repo", 999)
        assert result == [111, 222, 333]
        mock_sleep.assert_not_called()

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_empty_response(self, mock_run, mock_sleep):
        """Return empty list when stdout is empty."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        result = _fetch_review_comment_ids(42, "owner/repo", 999)
        assert result == []

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_retry_on_failure_then_succeed(self, mock_run, mock_sleep):
        """Retry on non-zero exit, succeed on second attempt."""
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="fail"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="10\n20\n", stderr=""),
        ]
        result = _fetch_review_comment_ids(42, "owner/repo", 999)
        assert result == [10, 20]
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once()

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_all_retries_exhausted(self, mock_run, mock_sleep):
        """Raise RuntimeError when all retries fail."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="network error")
        with pytest.raises(RuntimeError, match="Failed to fetch comment IDs"):
            _fetch_review_comment_ids(42, "owner/repo", 999)
        assert mock_run.call_count == 3  # 1 initial + 2 retries

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_whitespace_lines_ignored(self, mock_run, mock_sleep):
        """Blank lines in output are skipped."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="5\n\n  \n10\n", stderr="")
        result = _fetch_review_comment_ids(1, "o/r", 2)
        assert result == [5, 10]

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe", side_effect=OSError("gh not found"))
    def test_oserror_retries_then_raises(self, mock_run, mock_sleep):
        """Catch OSError from run_safe and retry, then raise RuntimeError."""
        with pytest.raises(RuntimeError, match="Failed to fetch comment IDs"):
            _fetch_review_comment_ids(42, "owner/repo", 999)
        assert mock_run.call_count == 3  # 1 initial + 2 retries

    @patch(f"{_MODULE}.time.sleep")
    @patch(f"{_MODULE}.run_safe")
    def test_oserror_then_success(self, mock_run, mock_sleep):
        """Recover from OSError on first attempt when second succeeds."""
        mock_run.side_effect = [
            OSError("permission denied"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="42\n", stderr=""),
        ]
        result = _fetch_review_comment_ids(1, "o/r", 2)
        assert result == [42]
        assert mock_run.call_count == 2
