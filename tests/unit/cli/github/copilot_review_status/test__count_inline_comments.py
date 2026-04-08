"""Tests for _count_inline_comments in copilot_review_status module."""

import json
import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.copilot_review_status import _count_inline_comments

MODULE = "agentic_devtools.cli.github.copilot_review_status"


def _ok(stdout: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "error") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


class TestCountInlineComments:
    """Tests for _count_inline_comments."""

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_three_comments(self, mock_run, mock_sleep):
        """Review with 3 inline comments returns 3."""
        comments = [
            {"body": "Fix this"},
            {"body": "And this"},
            {"body": "Also here"},
        ]
        stdout = "\n".join(json.dumps(c) for c in comments)
        mock_run.return_value = _ok(stdout)

        result = _count_inline_comments(42, "owner/repo", 100)

        assert result == 3

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_zero_comments(self, mock_run, mock_sleep):
        """Review with zero comments returns 0."""
        mock_run.return_value = _ok("")

        result = _count_inline_comments(42, "owner/repo", 100)

        assert result == 0

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_empty_body_not_counted(self, mock_run, mock_sleep):
        """Comments with empty body are not counted."""
        comments = [
            {"body": "Real comment"},
            {"body": ""},
            {"body": "   "},
        ]
        stdout = "\n".join(json.dumps(c) for c in comments)
        mock_run.return_value = _ok(stdout)

        result = _count_inline_comments(42, "owner/repo", 100)

        assert result == 1

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_retry_then_success(self, mock_run, mock_sleep):
        """Retries on failure and succeeds."""
        mock_run.side_effect = [
            _fail("server error"),
            _ok(json.dumps({"body": "comment"})),
        ]

        result = _count_inline_comments(42, "owner/repo", 100)

        assert result == 1
        mock_sleep.assert_called_once_with(10)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_all_retries_exhausted_raises(self, mock_run, mock_sleep):
        """All retries exhausted raises RuntimeError."""
        mock_run.return_value = _fail("persistent error")

        with pytest.raises(RuntimeError, match="Failed to fetch inline comments"):
            _count_inline_comments(42, "owner/repo", 100)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe", side_effect=OSError("gh not found"))
    def test_oserror_raises_runtime_error(self, mock_run, mock_sleep):
        """OSError from run_safe (gh not installed) raises RuntimeError."""
        with pytest.raises(RuntimeError, match="Failed to fetch inline comments"):
            _count_inline_comments(42, "owner/repo", 100)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_invalid_json_raises_runtime_error(self, mock_run, mock_sleep):
        """Invalid JSON in comment response raises RuntimeError."""
        mock_run.return_value = _ok("not valid json")

        with pytest.raises(RuntimeError, match="Failed to parse inline comment JSON"):
            _count_inline_comments(42, "owner/repo", 100)

    @patch(f"{MODULE}.time.sleep")
    @patch(f"{MODULE}.run_safe")
    def test_null_body_not_counted(self, mock_run, mock_sleep):
        """Comments with body=null are not counted (no AttributeError)."""
        comments = [
            {"body": None},
            {"body": "Real comment"},
        ]
        stdout = "\n".join(json.dumps(c) for c in comments)
        mock_run.return_value = _ok(stdout)

        result = _count_inline_comments(42, "owner/repo", 100)

        assert result == 1
