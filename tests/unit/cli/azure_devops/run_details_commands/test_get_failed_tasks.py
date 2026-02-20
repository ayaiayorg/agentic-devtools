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



class TestGetFailedTasks:
    """Tests for _get_failed_tasks helper."""

    def test_extracts_failed_tasks_with_logs(self):
        """Should extract failed Task records that have log URLs."""
        timeline_data = {
            "records": [
                {
                    "id": "1",
                    "name": "Build",
                    "type": "Task",
                    "result": "failed",
                    "log": {"id": 10, "url": "https://log.url/10"},
                },
                {
                    "id": "2",
                    "name": "Test",
                    "type": "Task",
                    "result": "succeeded",
                    "log": {"id": 11, "url": "https://log.url/11"},
                },
                {
                    "id": "3",
                    "name": "Deploy",
                    "type": "Task",
                    "result": "failed",
                    "log": {"id": 12, "url": "https://log.url/12"},
                },
            ]
        }

        failed = _get_failed_tasks(timeline_data)

        assert len(failed) == 2
        assert failed[0]["name"] == "Build"
        assert failed[0]["log_url"] == "https://log.url/10"
        assert failed[1]["name"] == "Deploy"

    def test_ignores_non_task_records(self):
        """Should only include Task type records, not Stage or Job."""
        timeline_data = {
            "records": [
                {
                    "id": "1",
                    "name": "Stage 1",
                    "type": "Stage",
                    "result": "failed",
                    "log": {"id": 10, "url": "https://log.url/10"},
                },
                {
                    "id": "2",
                    "name": "Job 1",
                    "type": "Job",
                    "result": "failed",
                    "log": {"id": 11, "url": "https://log.url/11"},
                },
                {
                    "id": "3",
                    "name": "Actual Task",
                    "type": "Task",
                    "result": "failed",
                    "log": {"id": 12, "url": "https://log.url/12"},
                },
            ]
        }

        failed = _get_failed_tasks(timeline_data)

        assert len(failed) == 1
        assert failed[0]["name"] == "Actual Task"

    def test_ignores_tasks_without_log_url(self):
        """Should skip tasks that don't have a log URL."""
        timeline_data = {
            "records": [
                {
                    "id": "1",
                    "name": "No Log Task",
                    "type": "Task",
                    "result": "failed",
                    "log": None,
                },
                {
                    "id": "2",
                    "name": "Empty Log Task",
                    "type": "Task",
                    "result": "failed",
                    "log": {"id": 10},  # No url
                },
                {
                    "id": "3",
                    "name": "Good Task",
                    "type": "Task",
                    "result": "failed",
                    "log": {"id": 12, "url": "https://log.url/12"},
                },
            ]
        }

        failed = _get_failed_tasks(timeline_data)

        assert len(failed) == 1
        assert failed[0]["name"] == "Good Task"

    def test_empty_records(self):
        """Should return empty list for no records."""
        timeline_data = {"records": []}
        failed = _get_failed_tasks(timeline_data)
        assert failed == []

    def test_no_records_key(self):
        """Should return empty list when records key is missing."""
        timeline_data = {}
        failed = _get_failed_tasks(timeline_data)
        assert failed == []
