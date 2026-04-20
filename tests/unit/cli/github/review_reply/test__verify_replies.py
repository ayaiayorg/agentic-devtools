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
        result = _verify_replies("owner/repo", 10, [1, 2])
        assert result == {1: True, 2: True}
        # Verify correct API endpoint includes pr_number
        call_args = mock_run.call_args[0][0]
        assert call_args[3] == "repos/owner/repo/pulls/10/comments"

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_some_unverified(self, mock_run):
        """Only found IDs are True; missing IDs are False."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        result = _verify_replies("owner/repo", 10, [1, 2])
        assert result == {1: True, 2: False}
        # Verify correct API endpoint includes pr_number
        call_args = mock_run.call_args[0][0]
        assert call_args[3] == "repos/owner/repo/pulls/10/comments"

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_empty_expected_list(self, mock_run):
        """Returns empty dict when no IDs are expected."""
        result = _verify_replies("owner/repo", 10, [])
        assert result == {}
        mock_run.assert_not_called()

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_api_failure(self, mock_run):
        """All IDs False when API call fails."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        result = _verify_replies("owner/repo", 10, [1, 2])
        assert result == {1: False, 2: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_invalid_json(self, mock_run):
        """Malformed lines are skipped; unmatched IDs are False."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        result = _verify_replies("owner/repo", 10, [1])
        assert result == {1: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_blank_lines_skipped(self, mock_run):
        """Blank lines in NDJSON output are skipped gracefully."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n\n\n{"id": 101, "in_reply_to_id": 2}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        result = _verify_replies("owner/repo", 10, [1, 2])
        assert result == {1: True, 2: True}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_empty_output(self, mock_run):
        """All IDs False when output is empty."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        result = _verify_replies("owner/repo", 10, [1])
        assert result == {1: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_precise_match_with_reply_map(self, mock_run):
        """Verifies by specific (reply_id, in_reply_to_id) pair when map provided."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n{"id": 101, "in_reply_to_id": 2}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        result = _verify_replies("owner/repo", 10, [1, 2], expected_reply_map={1: 100, 2: 101})
        assert result == {1: True, 2: True}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_reply_map_wrong_reply_id(self, mock_run):
        """False when reply_id in map does not match any fetched comment."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        # reply_id 999 does not exist — should be False even though in_reply_to_id=1 exists
        result = _verify_replies("owner/repo", 10, [1], expected_reply_map={1: 999})
        assert result == {1: False}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_reply_map_partial_coverage(self, mock_run):
        """Entries not in the map fall back to in_reply_to_id presence check."""
        ndjson = '{"id": 100, "in_reply_to_id": 1}\n{"id": 101, "in_reply_to_id": 2}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        # Only comment 1 has a known reply_id; comment 2 falls back to presence check
        result = _verify_replies("owner/repo", 10, [1, 2], expected_reply_map={1: 100})
        assert result == {1: True, 2: True}

    @patch("agentic_devtools.cli.github.review_reply.run_safe")
    def test_reply_map_false_positive_prevented(self, mock_run):
        """Prevents false positive from unrelated reply to same comment."""
        # Comment 1 has a reply (id=200) from a different actor, not our reply (id=100)
        ndjson = '{"id": 200, "in_reply_to_id": 1}\n'
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=ndjson, stderr="")
        # Without map: would be True (in_reply_to_id=1 exists)
        assert _verify_replies("owner/repo", 10, [1]) == {1: True}
        # With map: False because our specific reply (id=100) is not present
        result = _verify_replies("owner/repo", 10, [1], expected_reply_map={1: 100})
        assert result == {1: False}
