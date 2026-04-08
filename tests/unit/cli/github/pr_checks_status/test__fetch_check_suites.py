"""Tests for _fetch_check_suites function."""

import json
import subprocess
from unittest.mock import patch

from agentic_devtools.cli.github.pr_checks_status import _fetch_check_suites


class TestFetchCheckSuites:
    """Tests for check-suites API fetching and pagination."""

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_success_with_multiple_suites(self, mock_run):
        """Parses multiple newline-delimited JSON objects."""
        suites = [
            {"id": 1, "status": "completed", "conclusion": "success"},
            {"id": 2, "status": "completed", "conclusion": "success"},
        ]
        stdout = "\n".join(json.dumps(s) for s in suites)
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
        result = _fetch_check_suites("owner/repo", "abc123")
        assert len(result) == 2
        assert result[0]["id"] == 1

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_pagination_multiline(self, mock_run):
        """Handles paginated output with multiple lines."""
        lines = [json.dumps({"id": i, "status": "completed", "conclusion": "success"}) for i in range(5)]
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n".join(lines), stderr="")
        result = _fetch_check_suites("owner/repo", "sha123")
        assert len(result) == 5

    @patch("agentic_devtools.cli.github.pr_checks_status.time.sleep")
    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_retry_on_failure(self, mock_run, mock_sleep):
        """Retries on failure and succeeds on second attempt."""
        suite = {"id": 1, "status": "completed", "conclusion": "success"}
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(suite), stderr=""),
        ]
        result = _fetch_check_suites("owner/repo", "abc123")
        assert len(result) == 1
        mock_sleep.assert_called_once_with(10.0)

    @patch("agentic_devtools.cli.github.pr_checks_status.time.sleep")
    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_all_retries_exhausted_returns_empty(self, mock_run, mock_sleep):
        """Returns empty list when all retries exhausted (graceful degradation)."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad")
        result = _fetch_check_suites("owner/repo", "abc123")
        assert result == []
        assert mock_run.call_count == 3

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_empty_stdout(self, mock_run):
        """Empty stdout returns empty list."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        result = _fetch_check_suites("owner/repo", "abc123")
        assert result == []

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_command_args(self, mock_run):
        """Verify correct command arguments are passed."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        _fetch_check_suites("myorg/myrepo", "deadbeef")
        args = mock_run.call_args[0][0]
        assert args == [
            "gh",
            "api",
            "repos/myorg/myrepo/commits/deadbeef/check-suites?per_page=100",
            "--paginate",
            "--jq",
            ".check_suites[]",
        ]
        assert mock_run.call_args[1]["shell"] is False

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_whitespace_only_stdout(self, mock_run):
        """Whitespace-only stdout returns empty list."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="  \n  \n  ", stderr="")
        result = _fetch_check_suites("owner/repo", "abc123")
        assert result == []

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_gh_cli_not_found_returns_empty(self, mock_run):
        """Returns empty list with warning when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'gh'")
        result = _fetch_check_suites("owner/repo", "abc123")
        assert result == []
        assert mock_run.call_count == 1  # no retries on FileNotFoundError

    @patch("agentic_devtools.cli.github.pr_checks_status.time.sleep")
    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_json_parse_error_triggers_retry(self, mock_run, mock_sleep):
        """JSON parse error in check suites triggers retry."""
        suite = {"id": 1, "status": "completed", "conclusion": "success"}
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="not-valid-json", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(suite), stderr=""),
        ]
        result = _fetch_check_suites("owner/repo", "abc123")
        assert len(result) == 1
        mock_sleep.assert_called_once_with(10.0)
