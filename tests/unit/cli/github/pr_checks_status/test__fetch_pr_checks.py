"""Tests for _fetch_pr_checks function."""

import json
import subprocess
from unittest.mock import patch

import pytest

from agentic_devtools.cli.github.pr_checks_status import _fetch_pr_checks


class TestFetchPrChecks:
    """Tests for gh pr checks --json fetching and retry."""

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_success_first_try(self, mock_run):
        """Returns parsed checks on successful first attempt."""
        checks = [{"name": "build", "bucket": "pass"}]
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(checks), stderr="")
        result = _fetch_pr_checks(42, "owner/repo")
        assert result == checks
        assert mock_run.call_count == 1

    @patch("agentic_devtools.cli.github.pr_checks_status.time.sleep")
    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_retry_on_failure(self, mock_run, mock_sleep):
        """Retries on non-zero exit code and succeeds on second attempt."""
        checks = [{"name": "test", "bucket": "pass"}]
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(checks), stderr=""),
        ]
        result = _fetch_pr_checks(42, "owner/repo")
        assert result == checks
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once_with(10.0)

    @patch("agentic_devtools.cli.github.pr_checks_status.time.sleep")
    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_all_retries_exhausted(self, mock_run, mock_sleep):
        """sys.exit(1) when all retries exhausted."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad")
        with pytest.raises(SystemExit) as exc_info:
            _fetch_pr_checks(42, "owner/repo")
        assert exc_info.value.code == 1
        assert mock_run.call_count == 3  # initial + 2 retries

    @patch("agentic_devtools.cli.github.pr_checks_status.time.sleep")
    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_json_parse_error_triggers_retry(self, mock_run, mock_sleep):
        """JSON parse error triggers retry."""
        checks = [{"name": "build", "bucket": "pass"}]
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(checks), stderr=""),
        ]
        result = _fetch_pr_checks(42, "owner/repo")
        assert result == checks
        assert mock_run.call_count == 2

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_unexpected_json_type_triggers_retry(self, mock_run):
        """Non-list JSON response triggers retry."""
        checks = [{"name": "build", "bucket": "pass"}]
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout='{"not": "a list"}', stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(checks), stderr=""),
        ]
        with patch("agentic_devtools.cli.github.pr_checks_status.time.sleep"):
            result = _fetch_pr_checks(42, "owner/repo")
        assert result == checks

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_gh_cli_not_found(self, mock_run):
        """sys.exit(1) with helpful message when gh CLI is not installed."""
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'gh'")
        with pytest.raises(SystemExit) as exc_info:
            _fetch_pr_checks(42, "owner/repo")
        assert exc_info.value.code == 1
        assert mock_run.call_count == 1  # no retries on FileNotFoundError

    @patch("agentic_devtools.cli.github.pr_checks_status.run_safe")
    def test_command_args(self, mock_run):
        """Verify correct command arguments are passed."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        _fetch_pr_checks(123, "org/repo")
        args = mock_run.call_args[0][0]
        assert args == [
            "gh",
            "pr",
            "checks",
            "123",
            "--repo",
            "org/repo",
            "--json",
            "name,state,bucket,workflow,completedAt,description",
        ]
        assert mock_run.call_args[1]["shell"] is False
