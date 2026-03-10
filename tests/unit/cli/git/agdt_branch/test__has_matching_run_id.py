"""Tests for agentic_devtools.cli.git.agdt_branch._has_matching_run_id."""

from unittest.mock import patch

from agentic_devtools.cli.git.agdt_branch import _has_matching_run_id

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestHasMatchingRunId:
    """Tests for _has_matching_run_id()."""

    @patch(f"{_MOD}._read_commit_message", return_value="msg\n\nRun-Id: abc123")
    def test_returns_true_when_matching(self, _read):
        assert _has_matching_run_id("sha", "abc123") is True

    @patch(f"{_MOD}._read_commit_message", return_value="msg\n\nRun-Id: other")
    def test_returns_false_when_different(self, _read):
        assert _has_matching_run_id("sha", "abc123") is False

    @patch(f"{_MOD}._read_commit_message", return_value="")
    def test_returns_false_when_empty(self, _read):
        assert _has_matching_run_id("sha", "abc123") is False
