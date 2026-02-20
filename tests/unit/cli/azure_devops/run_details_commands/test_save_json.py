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



class TestSaveJson:
    """Tests for _save_json helper."""

    def test_saves_file_with_correct_name(self, tmp_path):
        """Should save JSON to correctly named file."""
        with patch(
            "agentic_devtools.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            data = {"test": "data"}
            filepath = _save_json(data, 12345, "pipeline")

            assert filepath.name == "temp-wb-patch-run-12345-pipeline.json"
            assert filepath.exists()

            with open(filepath) as f:
                saved_data = json.load(f)
            assert saved_data == {"test": "data"}

    def test_saves_error_file(self, tmp_path):
        """Should save error files with correct suffix."""
        with patch(
            "agentic_devtools.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            data = {"error": "Something went wrong"}
            filepath = _save_json(data, 99, "build-error")

            assert filepath.name == "temp-wb-patch-run-99-build-error.json"
            assert filepath.exists()
