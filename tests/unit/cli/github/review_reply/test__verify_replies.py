"""Tests for _verify_replies helper."""

import subprocess
from unittest.mock import patch

from agentic_devtools.cli.github.review_reply import _verify_replies


class TestVerifyReplies:
    """Tests for _verify_replies."""

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_all_verified(self, mock_run):
        """All expected IDs found in in_reply_to_id."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n{"id": 101, "in_reply_to_id": 2}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        result = _verify_replies("owner/repo", 10, 999, [1, 2])
        assert result == {1: True, 2: True}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_some_unverified(self, mock_run):
        """Only found IDs are True; missing IDs are False."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        result = _verify_replies("owner/repo", 10, 999, [1, 2])
        assert result == {1: True, 2: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_empty_expected_list(self, mock_run):
        """Returns empty dict when no IDs are expected."""
        result = _verify_replies("owner/repo", 10, 999, [])
        assert result == {}
        mock_run.assert_not_called()

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_api_failure(self, mock_run):
        """All IDs False when API call fails."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        result = _verify_replies("owner/repo", 10, 999, [1, 2])
        assert result == {1: False, 2: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_invalid_json(self, mock_run):
        """Malformed lines are skipped; unmatched IDs are False."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        result = _verify_replies("owner/repo", 10, 999, [1])
        assert result == {1: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_blank_lines_skipped(self, mock_run):
        """Blank lines in NDJSON output are skipped gracefully."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n\n\n{"id": 101, "in_reply_to_id": 2}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        result = _verify_replies("owner/repo", 10, 999, [1, 2])
        assert result == {1: True, 2: True}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_empty_output(self, mock_run):
        """All IDs False when output is empty."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        result = _verify_replies("owner/repo", 10, 999, [1])
        assert result == {1: False}
