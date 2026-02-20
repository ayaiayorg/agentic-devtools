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



class TestPrintParameters:
    """Tests for _print_parameters helper."""

    def test_pipeline_template_parameters(self, capsys):
        """Should print templateParameters for pipeline source."""
        data = {"templateParameters": {"env": "dev", "deploy": "true"}}
        _print_parameters(data, "pipeline")

        captured = capsys.readouterr()
        assert "env: dev" in captured.out
        assert "deploy: true" in captured.out

    def test_build_json_parameters(self, capsys):
        """Should parse JSON parameters for build source."""
        data = {"parameters": '{"env": "prod", "version": "1.0"}'}
        _print_parameters(data, "build")

        captured = capsys.readouterr()
        assert "env: prod" in captured.out
        assert "version: 1.0" in captured.out

    def test_no_parameters(self, capsys):
        """Should print (none) when no parameters present."""
        data = {}
        _print_parameters(data, "build")

        captured = capsys.readouterr()
        assert "(none)" in captured.out

    def test_invalid_json_parameters(self, capsys):
        """Should handle invalid JSON in build parameters."""
        data = {"parameters": "not-valid-json"}
        _print_parameters(data, "build")

        captured = capsys.readouterr()
        assert "raw" in captured.out
