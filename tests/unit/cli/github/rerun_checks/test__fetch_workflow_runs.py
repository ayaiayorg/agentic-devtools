"""Tests for _fetch_workflow_runs."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.github.rerun_checks import _fetch_workflow_runs

_MOD = "agentic_devtools.cli.github.rerun_checks"


class TestFetchWorkflowRuns:
    """Tests for _fetch_workflow_runs."""

    @patch(f"{_MOD}.run_safe")
    def test_success_first_try(self, mock_run):
        """Returns parsed workflow runs on first successful call."""
        runs = [
            {"id": 1, "name": "CI", "conclusion": "failure"},
            {"id": 2, "name": "Lint", "conclusion": "success"},
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="\n".join(json.dumps(r) for r in runs),
        )

        result = _fetch_workflow_runs("owner/repo", "abc123")

        assert result == runs
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "repos/owner/repo/actions/runs?head_sha=abc123&per_page=100" in args[2]

    @patch(f"{_MOD}.time.sleep")
    @patch(f"{_MOD}.run_safe")
    def test_retry_on_failure_then_success(self, mock_run, mock_sleep):
        """Retries on non-zero exit code, then succeeds."""
        fail_result = MagicMock(returncode=1, stderr="timeout")
        success_result = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 1, "name": "CI", "conclusion": "failure"}),
        )
        mock_run.side_effect = [fail_result, success_result]

        result = _fetch_workflow_runs("owner/repo", "abc123")

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert mock_run.call_count == 2
        mock_sleep.assert_called_once_with(10.0)

    @patch(f"{_MOD}.time.sleep")
    @patch(f"{_MOD}.run_safe")
    def test_all_retries_exhausted_exits(self, mock_run, mock_sleep):
        """Calls sys.exit(1) after all retries fail."""
        mock_run.return_value = MagicMock(returncode=1, stderr="API error")

        with pytest.raises(SystemExit) as exc_info:
            _fetch_workflow_runs("owner/repo", "sha")

        assert exc_info.value.code == 1
        assert mock_run.call_count == 3  # initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch(f"{_MOD}.time.sleep")
    @patch(f"{_MOD}.run_safe")
    def test_json_parse_error_triggers_retry(self, mock_run, mock_sleep):
        """Retries when JSON parsing fails."""
        bad_result = MagicMock(returncode=0, stdout="not-json")
        good_result = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 1, "name": "CI", "conclusion": "failure"}),
        )
        mock_run.side_effect = [bad_result, good_result]

        result = _fetch_workflow_runs("owner/repo", "sha")

        assert len(result) == 1
        mock_sleep.assert_called_once_with(10.0)

    @patch(f"{_MOD}.run_safe")
    def test_empty_stdout_returns_empty_list(self, mock_run):
        """Empty stdout (no runs) returns an empty list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = _fetch_workflow_runs("owner/repo", "sha")

        assert result == []

    @patch(f"{_MOD}.run_safe")
    def test_paginated_multiline_output(self, mock_run):
        """Multiline output (multiple JSON objects) is parsed correctly."""
        lines = [json.dumps({"id": i, "name": f"wf{i}", "conclusion": "failure"}) for i in range(5)]
        mock_run.return_value = MagicMock(returncode=0, stdout="\n".join(lines))

        result = _fetch_workflow_runs("owner/repo", "sha")

        assert len(result) == 5
        assert [r["id"] for r in result] == list(range(5))

    @patch(f"{_MOD}.time.sleep")
    @patch(f"{_MOD}.run_safe")
    def test_json_parse_error_all_retries_exhausted(self, mock_run, mock_sleep):
        """Exits with code 1 when all retries fail due to JSON parse error."""
        mock_run.return_value = MagicMock(returncode=0, stdout="not-json\n")

        with pytest.raises(SystemExit) as exc_info:
            _fetch_workflow_runs("owner/repo", "sha")

        assert exc_info.value.code == 1
        assert mock_run.call_count == 3
        assert mock_sleep.call_count == 2

    @patch(f"{_MOD}.run_safe", side_effect=FileNotFoundError)
    def test_gh_not_installed_exits(self, mock_run, capsys):
        """Exits with code 1 and clear message when gh CLI is not found."""
        with pytest.raises(SystemExit) as exc_info:
            _fetch_workflow_runs("owner/repo", "sha")

        assert exc_info.value.code == 1
        assert "gh" in capsys.readouterr().err.lower()

    @patch(f"{_MOD}.run_safe", side_effect=OSError("Permission denied"))
    def test_oserror_exits_with_clear_message(self, mock_run, capsys):
        """Exits with code 1 and clear message on OSError (e.g., permission denied)."""
        with pytest.raises(SystemExit) as exc_info:
            _fetch_workflow_runs("owner/repo", "sha")

        assert exc_info.value.code == 1
        captured = capsys.readouterr().err
        assert "Failed to execute 'gh' CLI" in captured
        assert "Permission denied" in captured
