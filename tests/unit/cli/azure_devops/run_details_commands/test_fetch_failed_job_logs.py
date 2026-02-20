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



class TestFetchFailedJobLogs:
    """Tests for fetch_failed_job_logs function."""

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._fetch_build_timeline")
    def test_returns_error_on_timeline_failure(self, mock_timeline, mock_pat, mock_requests):
        """Should return error when timeline fetch fails."""
        mock_pat.return_value = "fake-pat"
        mock_timeline.return_value = (None, "Timeline error")

        result = fetch_failed_job_logs(123)

        assert result["success"] is False
        assert "Timeline error" in result["error"]

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._fetch_build_timeline")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._get_failed_tasks")
    def test_success_with_no_failed_tasks(self, mock_get_failed, mock_timeline, mock_pat, mock_requests):
        """Should return success when no failed tasks found."""
        mock_pat.return_value = "fake-pat"
        mock_timeline.return_value = ({"records": []}, None)
        mock_get_failed.return_value = []

        result = fetch_failed_job_logs(123)

        assert result["success"] is True
        assert result["failed_tasks"] == []

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._fetch_build_timeline")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._get_failed_tasks")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._fetch_task_log")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._save_log_file")
    def test_fetches_and_saves_logs(
        self,
        mock_save,
        mock_fetch_log,
        mock_get_failed,
        mock_timeline,
        mock_pat,
        mock_requests,
    ):
        """Should fetch and save logs for failed tasks with vpn_toggle=False."""
        mock_pat.return_value = "fake-pat"
        mock_timeline.return_value = ({"records": []}, None)
        mock_get_failed.return_value = [{"name": "Build", "log_url": "https://log.url/1"}]
        mock_fetch_log.return_value = ("Log content here", None)
        mock_save.return_value = "/tmp/build.log"

        # Use vpn_toggle=False to avoid VpnToggleContext path
        result = fetch_failed_job_logs(123, vpn_toggle=False)

        assert result["success"] is True
        assert len(result["log_files"]) == 1
        assert result["log_files"][0]["task_name"] == "Build"
