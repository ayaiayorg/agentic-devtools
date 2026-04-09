"""Tests for _verify_merge helper."""

import json
from types import SimpleNamespace
from unittest.mock import patch

from agentic_devtools.cli.github import pr_merge


class TestVerifyMerge:
    """Tests for _verify_merge."""

    def test_merged_state(self):
        """Returns MERGED state with mergedAt."""
        data = {"state": "MERGED", "mergedAt": "2026-04-07T09:05:55Z"}
        mock_result = SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "MERGED"
        assert result["mergedAt"] == "2026-04-07T09:05:55Z"

    def test_open_state(self):
        """Returns OPEN state."""
        data = {"state": "OPEN", "mergedAt": None}
        mock_result = SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "OPEN"
        assert result["mergedAt"] is None

    def test_closed_state_no_merged_at(self):
        """Returns CLOSED state with null mergedAt."""
        data = {"state": "CLOSED", "mergedAt": None}
        mock_result = SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "CLOSED"
        assert result["mergedAt"] is None

    def test_api_failure_returns_unknown(self):
        """Non-zero exit returns UNKNOWN state."""
        mock_result = SimpleNamespace(returncode=1, stdout="", stderr="error")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "UNKNOWN"
        assert result["mergedAt"] is None

    def test_malformed_json_returns_unknown(self):
        """Malformed JSON response returns UNKNOWN state."""
        mock_result = SimpleNamespace(returncode=0, stdout="not json", stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "UNKNOWN"
        assert result["mergedAt"] is None

    def test_shell_false_used(self):
        """shell=False is passed to run_safe."""
        data = {"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z"}
        mock_result = SimpleNamespace(returncode=0, stdout=json.dumps(data), stderr="")
        with patch.object(pr_merge, "run_safe", return_value=mock_result) as mock_run:
            pr_merge._verify_merge(42, "o/r")

        assert mock_run.call_args[1]["shell"] is False

    def test_file_not_found_error_returns_unknown(self):
        """FileNotFoundError from run_safe returns UNKNOWN state."""
        with patch.object(pr_merge, "run_safe", side_effect=FileNotFoundError("gh not found")):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "UNKNOWN"
        assert result["mergedAt"] is None

    def test_os_error_returns_unknown(self):
        """OSError from run_safe returns UNKNOWN state."""
        with patch.object(pr_merge, "run_safe", side_effect=OSError("permission denied")):
            result = pr_merge._verify_merge(42, "o/r")

        assert result["state"] == "UNKNOWN"
        assert result["mergedAt"] is None
