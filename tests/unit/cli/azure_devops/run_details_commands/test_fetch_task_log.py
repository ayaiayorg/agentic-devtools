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



class TestFetchTaskLog:
    """Tests for _fetch_task_log helper."""

    def test_success_returns_log_content(self):
        """Should return log text on successful response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.text = "Log line 1\nLog line 2\nError occurred"
        mock_requests.get.return_value = response

        content, error = _fetch_task_log(mock_requests, {}, "https://dev.azure.com/org/project/_apis/logs/123")

        assert content == "Log line 1\nLog line 2\nError occurred"
        assert error is None

    def test_failure_returns_error(self):
        """Should return error on non-200 response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 500
        mock_requests.get.return_value = response

        content, error = _fetch_task_log(mock_requests, {}, "https://dev.azure.com/org/project/_apis/logs/123")

        assert content is None
        assert "500" in error

    def test_exception_returns_error(self):
        """Should return error on exception."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Connection refused")

        content, error = _fetch_task_log(mock_requests, {}, "https://dev.azure.com/org/project/_apis/logs/123")

        assert content is None
        assert "Connection refused" in error
