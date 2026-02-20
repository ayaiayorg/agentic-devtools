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



class TestIsRunFinished:
    """Tests for _is_run_finished helper."""

    def test_completed_build_with_result(self):
        """Should return True for completed build status."""
        data = {"status": "completed", "result": "succeeded"}
        is_finished, result = _is_run_finished(data)
        assert is_finished is True
        assert result == "succeeded"

    def test_cancelled_build(self):
        """Should return True for cancelled status."""
        data = {"status": "cancelled", "result": "canceled"}
        is_finished, result = _is_run_finished(data)
        assert is_finished is True
        assert result == "canceled"

    def test_in_progress_build(self):
        """Should return False for inProgress status."""
        data = {"status": "inProgress", "result": None}
        is_finished, result = _is_run_finished(data)
        assert is_finished is False
        assert result is None

    def test_pipeline_state_completed(self):
        """Should return True for completed pipeline state."""
        data = {"state": "completed", "result": "failed"}
        is_finished, result = _is_run_finished(data)
        assert is_finished is True
        assert result == "failed"

    def test_pipeline_state_running(self):
        """Should return False for running pipeline state."""
        data = {"state": "running", "result": None}
        is_finished, result = _is_run_finished(data)
        assert is_finished is False
        assert result is None
