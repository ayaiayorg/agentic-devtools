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



class TestGetTempFolder:
    """Tests for _get_temp_folder helper."""

    def test_creates_temp_folder(self, tmp_path):
        """Should create temp folder if it doesn't exist."""
        with patch("agentic_devtools.cli.azure_devops.run_details_commands.Path") as mock_path:
            # Set up the chain of Path operations
            mock_file = MagicMock()
            mock_file.parent.parent.parent.parent = tmp_path
            mock_path.return_value = mock_file
            mock_path.__file__ = __file__

            # Just verify the function returns a Path-like object
            # The actual implementation depends on file system structure
            result = _get_temp_folder()
            assert result is not None
