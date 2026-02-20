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



class TestSaveLogFile:
    """Tests for _save_log_file helper."""

    def test_saves_log_with_sanitized_name(self, tmp_path):
        """Should save log file with sanitized task name."""
        with patch(
            "agentic_devtools.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            filepath = _save_log_file(
                "Error: Build failed\nStack trace here",
                12345,
                "My Task Name!@#$%",
            )

            assert filepath.exists()
            assert "temp-run-12345-My_Task_Name_____" in filepath.name
            assert filepath.suffix == ".log"

            content = filepath.read_text()
            assert "Error: Build failed" in content

    def test_truncates_long_task_names(self, tmp_path):
        """Should truncate very long task names to 50 chars."""
        with patch(
            "agentic_devtools.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            long_name = "A" * 100
            filepath = _save_log_file("content", 1, long_name)

            # The safe_name should be truncated to 50 chars
            assert filepath.exists()
            # Count the A's in the filename
            name_part = filepath.stem.split("-")[3]  # After "temp-run-1-"
            assert len(name_part) <= 50
