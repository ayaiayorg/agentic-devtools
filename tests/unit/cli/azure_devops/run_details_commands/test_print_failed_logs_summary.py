"""
Tests for run_details_commands module.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops import get_run_details
from agentic_devtools.cli.azure_devops.run_details_commands import (
    _fetch_build_run,
    _fetch_build_timeline,
    _fetch_pipeline_run,
    _fetch_task_log,
    _get_failed_tasks,
    _get_temp_folder,
    _is_run_finished,
    _print_failed_logs_summary,
    _print_parameters,
    _print_summary,
    _save_json,
    _save_log_file,
    fetch_failed_job_logs,
    get_run_details_impl,
    wait_for_run,
    wait_for_run_impl,
)



class TestPrintFailedLogsSummary:
    """Tests for _print_failed_logs_summary helper."""

    def test_prints_error_when_not_success(self, capsys):
        """Should print error message when fetch failed."""
        log_result = {
            "success": False,
            "error": "Network timeout",
            "failed_tasks": [],
            "log_files": [],
        }

        _print_failed_logs_summary(log_result, 123)

        captured = capsys.readouterr()
        assert "Could not fetch failure logs" in captured.out
        assert "Network timeout" in captured.out

    def test_prints_no_failed_tasks_message(self, capsys):
        """Should print message when no failed tasks found."""
        log_result = {
            "success": True,
            "error": None,
            "failed_tasks": [],
            "log_files": [],
        }

        _print_failed_logs_summary(log_result, 123)

        captured = capsys.readouterr()
        assert "No failed tasks found" in captured.out

    def test_prints_failed_tasks_and_log_files(self, capsys):
        """Should print failed tasks and saved log file paths."""
        log_result = {
            "success": True,
            "error": None,
            "failed_tasks": [
                {"name": "Build Step"},
                {"name": "Test Step"},
            ],
            "log_files": [
                {"task_name": "Build Step", "path": "/tmp/build.log"},
                {"task_name": "Test Step", "path": "/tmp/test.log"},
            ],
        }

        _print_failed_logs_summary(log_result, 123)

        captured = capsys.readouterr()
        assert "FAILED TASK LOGS" in captured.out
        assert "2 failed task(s)" in captured.out
        assert "Build Step" in captured.out
        assert "Test Step" in captured.out
        assert "/tmp/build.log" in captured.out
