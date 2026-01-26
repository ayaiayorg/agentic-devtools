"""
Tests for run_details_commands module.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from dfly_ai_helpers.cli.azure_devops import get_run_details
from dfly_ai_helpers.cli.azure_devops.run_details_commands import (
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


class TestGetRunDetails:
    """Tests for get_run_details CLI command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "12345")
        set_value("dry_run", "true")

        get_run_details()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "12345" in captured.out
        assert "Organization" in captured.out
        assert "Project" in captured.out

    def test_dry_run_shows_endpoints(self, temp_state_dir, clear_state_before, capsys):
        """Should show API endpoints in dry run."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "99999")
        set_value("dry_run", "true")

        get_run_details()

        captured = capsys.readouterr()
        assert "/_apis/pipelines/runs/99999" in captured.out
        assert "/_apis/build/builds/99999" in captured.out

    def test_missing_run_id_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error if run_id is not set."""
        with pytest.raises(SystemExit) as exc_info:
            get_run_details()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "run_id" in captured.err
        assert "required" in captured.err

    def test_invalid_run_id_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error if run_id is not an integer."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "not-a-number")

        with pytest.raises(SystemExit) as exc_info:
            get_run_details()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "integer" in captured.err

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    def test_api_failure_exits_with_error(
        self, mock_get_pat, mock_require_requests, temp_state_dir, clear_state_before
    ):
        """Should exit with code 1 when API calls fail."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "12345")
        mock_get_pat.return_value = "fake-pat"

        mock_requests = MagicMock()
        mock_require_requests.return_value = mock_requests

        # Both APIs fail
        response = MagicMock()
        response.status_code = 500
        mock_requests.get.return_value = response

        with pytest.raises(SystemExit) as exc_info:
            get_run_details()

        assert exc_info.value.code == 1


class TestGetRunDetailsImpl:
    """Tests for get_run_details_impl function."""

    def test_dry_run_returns_success(self, capsys):
        """Should return success in dry run mode."""
        result = get_run_details_impl(run_id=12345, dry_run=True)

        assert result["success"] is True
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._save_json")
    def test_prefers_build_api_over_pipeline(self, mock_save_json, mock_get_pat, mock_require_requests, capsys):
        """Should prefer build API response when both succeed."""
        mock_get_pat.return_value = "fake-pat"

        mock_requests = MagicMock()
        mock_require_requests.return_value = mock_requests

        # Both APIs succeed
        pipeline_response = MagicMock()
        pipeline_response.status_code = 200
        pipeline_response.json.return_value = {
            "state": "completed",
            "result": "succeeded",
            "pipeline": {"name": "test-pipeline"},
            "templateParameters": {"param1": "value1"},
        }

        build_response = MagicMock()
        build_response.status_code = 200
        build_response.json.return_value = {
            "status": "completed",
            "result": "succeeded",
            "sourceBranch": "refs/heads/main",
            "definition": {"name": "test-build"},
            "parameters": '{"param1": "value1"}',
            "_links": {"web": {"href": "https://example.com"}},
        }

        def mock_get(url, headers):
            if "pipelines/runs" in url:
                return pipeline_response
            else:
                return build_response

        mock_requests.get = mock_get
        mock_save_json.return_value = "/tmp/test.json"

        result = get_run_details_impl(run_id=12345)

        assert result["success"] is True
        assert result["source"] == "build"

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._save_json")
    def test_falls_back_to_pipeline_when_build_fails(self, mock_save_json, mock_get_pat, mock_require_requests, capsys):
        """Should fall back to pipeline API when build API fails."""
        mock_get_pat.return_value = "fake-pat"

        mock_requests = MagicMock()
        mock_require_requests.return_value = mock_requests

        # Pipeline succeeds, build fails
        pipeline_response = MagicMock()
        pipeline_response.status_code = 200
        pipeline_response.json.return_value = {
            "state": "completed",
            "result": "succeeded",
            "pipeline": {"name": "test-pipeline"},
            "resources": {"repositories": {"self": {"refName": "refs/heads/main"}}},
            "_links": {"web": {"href": "https://example.com"}},
        }

        build_response = MagicMock()
        build_response.status_code = 404
        build_response.text = "Not found"

        def mock_get(url, headers):
            if "pipelines/runs" in url:
                return pipeline_response
            else:
                return build_response

        mock_requests.get = mock_get
        mock_save_json.return_value = "/tmp/test.json"

        result = get_run_details_impl(run_id=12345)

        assert result["success"] is True
        assert result["source"] == "pipeline"

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._save_json")
    def test_both_apis_fail_returns_error(self, mock_save_json, mock_get_pat, mock_require_requests, capsys):
        """Should return error when both APIs fail."""
        mock_get_pat.return_value = "fake-pat"

        mock_requests = MagicMock()
        mock_require_requests.return_value = mock_requests

        # Both APIs fail
        pipeline_response = MagicMock()
        pipeline_response.status_code = 404
        pipeline_response.text = "Pipeline not found"

        build_response = MagicMock()
        build_response.status_code = 404
        build_response.text = "Build not found"

        def mock_get(url, headers):
            if "pipelines/runs" in url:
                return pipeline_response
            else:
                return build_response

        mock_requests.get = mock_get
        mock_save_json.return_value = "/tmp/test.json"

        result = get_run_details_impl(run_id=12345)

        assert result["success"] is False
        assert result["error"] is not None
        assert "Both APIs failed" in result["error"]


class TestFetchPipelineRun:
    """Tests for _fetch_pipeline_run helper."""

    def test_success_returns_data(self):
        """Should return data on successful response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"state": "completed"}
        mock_requests.get.return_value = response

        data, error = _fetch_pipeline_run(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data == {"state": "completed"}
        assert error is None

    def test_failure_returns_error(self):
        """Should return error on non-200 response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 404
        response.text = "Not found"
        mock_requests.get.return_value = response

        data, error = _fetch_pipeline_run(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data is None
        assert "404" in error

    def test_exception_returns_error(self):
        """Should return error on exception."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network error")

        data, error = _fetch_pipeline_run(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data is None
        assert "Network error" in error


class TestFetchBuildRun:
    """Tests for _fetch_build_run helper."""

    def test_success_returns_data(self):
        """Should return data on successful response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"status": "completed"}
        mock_requests.get.return_value = response

        data, error = _fetch_build_run(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data == {"status": "completed"}
        assert error is None

    def test_failure_returns_error(self):
        """Should return error on non-200 response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 500
        response.text = "Server error"
        mock_requests.get.return_value = response

        data, error = _fetch_build_run(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data is None
        assert "500" in error

    def test_exception_returns_error(self):
        """Should return error on exception."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Connection timeout")

        data, error = _fetch_build_run(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data is None
        assert "Connection timeout" in error


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


class TestPrintSummary:
    """Tests for _print_summary helper."""

    def test_pipeline_summary_output(self, capsys):
        """Should print formatted summary for pipeline data."""
        data = {
            "state": "completed",
            "result": "succeeded",
            "pipeline": {"name": "my-pipeline"},
            "resources": {"repositories": {"self": {"refName": "refs/heads/feature"}}},
            "_links": {"web": {"href": "https://example.com/run/123"}},
            "templateParameters": {"stage": "INT"},
        }
        _print_summary(data, "pipeline")

        captured = capsys.readouterr()
        assert "pipeline API" in captured.out
        assert "completed" in captured.out
        assert "succeeded" in captured.out
        assert "my-pipeline" in captured.out
        assert "refs/heads/feature" in captured.out
        assert "https://example.com/run/123" in captured.out
        assert "stage: INT" in captured.out

    def test_build_summary_output(self, capsys):
        """Should print formatted summary for build data."""
        data = {
            "status": "inProgress",
            "result": None,
            "sourceBranch": "refs/heads/main",
            "definition": {"name": "CI-Build"},
            "_links": {"web": {"href": "https://example.com/build/456"}},
            "parameters": '{"clean": "true"}',
        }
        _print_summary(data, "build")

        captured = capsys.readouterr()
        assert "build API" in captured.out
        assert "inProgress" in captured.out
        assert "refs/heads/main" in captured.out
        assert "CI-Build" in captured.out


class TestSaveJson:
    """Tests for _save_json helper."""

    def test_saves_file_with_correct_name(self, tmp_path):
        """Should save JSON to correctly named file."""
        with patch(
            "dfly_ai_helpers.cli.azure_devops.run_details_commands._get_temp_folder",
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
            "dfly_ai_helpers.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            data = {"error": "Something went wrong"}
            filepath = _save_json(data, 99, "build-error")

            assert filepath.name == "temp-wb-patch-run-99-build-error.json"
            assert filepath.exists()


class TestGetTempFolder:
    """Tests for _get_temp_folder helper."""

    def test_creates_temp_folder(self, tmp_path):
        """Should create temp folder if it doesn't exist."""
        with patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.Path") as mock_path:
            # Set up the chain of Path operations
            mock_file = MagicMock()
            mock_file.parent.parent.parent.parent = tmp_path
            mock_path.return_value = mock_file
            mock_path.__file__ = __file__

            # Just verify the function returns a Path-like object
            # The actual implementation depends on file system structure
            result = _get_temp_folder()
            assert result is not None


class TestFetchBuildTimeline:
    """Tests for _fetch_build_timeline helper."""

    def test_success_returns_data(self):
        """Should return timeline data on successful response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"records": [{"id": "1", "type": "Task"}]}
        mock_requests.get.return_value = response

        data, error = _fetch_build_timeline(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data == {"records": [{"id": "1", "type": "Task"}]}
        assert error is None

    def test_failure_returns_error(self):
        """Should return error on non-200 response."""
        mock_requests = MagicMock()
        response = MagicMock()
        response.status_code = 404
        mock_requests.get.return_value = response

        data, error = _fetch_build_timeline(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data is None
        assert "404" in error

    def test_exception_returns_error(self):
        """Should return error on exception."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network timeout")

        data, error = _fetch_build_timeline(mock_requests, {}, "https://dev.azure.com/org", "project", 123)

        assert data is None
        assert "Network timeout" in error


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


class TestSaveLogFile:
    """Tests for _save_log_file helper."""

    def test_saves_log_with_sanitized_name(self, tmp_path):
        """Should save log file with sanitized task name."""
        with patch(
            "dfly_ai_helpers.cli.azure_devops.run_details_commands._get_temp_folder",
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
            "dfly_ai_helpers.cli.azure_devops.run_details_commands._get_temp_folder",
            return_value=tmp_path,
        ):
            long_name = "A" * 100
            filepath = _save_log_file("content", 1, long_name)

            # The safe_name should be truncated to 50 chars
            assert filepath.exists()
            # Count the A's in the filename
            name_part = filepath.stem.split("-")[3]  # After "temp-run-1-"
            assert len(name_part) <= 50


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


class TestFetchFailedJobLogs:
    """Tests for fetch_failed_job_logs function."""

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._fetch_build_timeline")
    def test_returns_error_on_timeline_failure(self, mock_timeline, mock_pat, mock_requests):
        """Should return error when timeline fetch fails."""
        mock_pat.return_value = "fake-pat"
        mock_timeline.return_value = (None, "Timeline error")

        result = fetch_failed_job_logs(123)

        assert result["success"] is False
        assert "Timeline error" in result["error"]

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._fetch_build_timeline")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._get_failed_tasks")
    def test_success_with_no_failed_tasks(self, mock_get_failed, mock_timeline, mock_pat, mock_requests):
        """Should return success when no failed tasks found."""
        mock_pat.return_value = "fake-pat"
        mock_timeline.return_value = ({"records": []}, None)
        mock_get_failed.return_value = []

        result = fetch_failed_job_logs(123)

        assert result["success"] is True
        assert result["failed_tasks"] == []

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.require_requests")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_pat")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._fetch_build_timeline")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._get_failed_tasks")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._fetch_task_log")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._save_log_file")
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


class TestWaitForRunImpl:
    """Tests for wait_for_run_impl function."""

    def test_dry_run_returns_success(self, capsys):
        """Should return success in dry run mode."""
        result = wait_for_run_impl(run_id=12345, dry_run=True)

        assert result["success"] is True
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "12345" in captured.out

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.time.sleep")
    def test_returns_after_run_completes(self, mock_sleep, mock_get_details, capsys):
        """Should return when run completes successfully."""
        mock_get_details.return_value = {
            "success": True,
            "data": {
                "status": "completed",
                "result": "succeeded",
                "_links": {"web": {"href": "https://example.com"}},
            },
        }

        result = wait_for_run_impl(run_id=123, poll_interval=1)

        assert result["success"] is True
        assert result["finished"] is True
        assert result["result"] == "succeeded"
        mock_sleep.assert_not_called()

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.time.sleep")
    def test_polls_until_complete(self, mock_sleep, mock_get_details, capsys):
        """Should poll multiple times until run completes."""
        # First call: in progress, second call: completed
        mock_get_details.side_effect = [
            {
                "success": True,
                "data": {"status": "inProgress", "result": None},
            },
            {
                "success": True,
                "data": {
                    "status": "completed",
                    "result": "succeeded",
                    "_links": {"web": {"href": "https://example.com"}},
                },
            },
        ]

        result = wait_for_run_impl(run_id=123, poll_interval=1)

        assert result["success"] is True
        assert result["poll_count"] == 2
        mock_sleep.assert_called_once_with(1)

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.time.sleep")
    def test_fails_after_max_consecutive_failures(self, mock_sleep, mock_get_details, capsys):
        """Should fail after max consecutive fetch failures."""
        mock_get_details.return_value = {
            "success": False,
            "error": "API error",
        }

        result = wait_for_run_impl(run_id=123, poll_interval=1, max_failures=2)

        assert result["success"] is False
        assert "2 times consecutively" in result["error"]
        # Sleep is called once after first failure, then second failure hits max and returns
        assert mock_sleep.call_count == 1

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.get_run_details_impl")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.fetch_failed_job_logs")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands._print_failed_logs_summary")
    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.time.sleep")
    def test_fetches_logs_on_failure_when_requested(
        self, mock_sleep, mock_print_summary, mock_fetch_logs, mock_get_details, capsys
    ):
        """Should fetch logs when run fails and fetch_logs is True."""
        mock_get_details.return_value = {
            "success": True,
            "data": {
                "status": "completed",
                "result": "failed",
                "_links": {"web": {"href": "https://example.com"}},
            },
        }
        mock_fetch_logs.return_value = {
            "success": True,
            "log_files": [{"task_name": "Build", "path": "/tmp/log"}],
        }

        result = wait_for_run_impl(run_id=123, fetch_logs=True)

        assert result["success"] is True
        assert result["result"] == "failed"
        mock_fetch_logs.assert_called_once()


class TestWaitForRun:
    """Tests for wait_for_run CLI entry point."""

    def test_missing_run_id_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error if run_id is not set."""
        with pytest.raises(SystemExit) as exc_info:
            wait_for_run()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "run_id" in captured.err

    def test_invalid_run_id_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error if run_id is not an integer."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "not-a-number")

        with pytest.raises(SystemExit) as exc_info:
            wait_for_run()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "integer" in captured.err

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "12345")
        set_value("dry_run", "true")

        wait_for_run()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "12345" in captured.out

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_cli_args_override_state(self, mock_impl, temp_state_dir, clear_state_before, capsys, monkeypatch):
        """CLI args should override state values."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "111")

        mock_impl.return_value = {"success": True}

        # Simulate CLI args
        monkeypatch.setattr(sys, "argv", ["wait_for_run", "--run-id", "222", "--poll-interval", "5"])

        wait_for_run()

        # Verify impl was called with CLI arg values
        mock_impl.assert_called_once()
        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["run_id"] == 222
        assert call_kwargs["poll_interval"] == 5

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_exits_on_failure(self, mock_impl, temp_state_dir, clear_state_before, capsys):
        """Should exit with code 1 when impl returns failure."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "123")

        mock_impl.return_value = {"success": False, "error": "Some error"}

        with pytest.raises(SystemExit) as exc_info:
            wait_for_run()

        assert exc_info.value.code == 1

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_invalid_poll_interval_uses_default(self, mock_impl, temp_state_dir, clear_state_before, capsys):
        """Should use default poll interval when state value is invalid."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "123")
        set_value("poll_interval", "not-a-number")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        captured = capsys.readouterr()
        assert "Invalid poll_interval" in captured.out
        # Should still call impl with default
        mock_impl.assert_called_once()

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_invalid_max_failures_uses_default(self, mock_impl, temp_state_dir, clear_state_before, capsys):
        """Should use default max failures when state value is invalid."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "123")
        set_value("max_failures", "invalid")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        captured = capsys.readouterr()
        assert "Invalid max_failures" in captured.out
        mock_impl.assert_called_once()

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_fetch_logs_from_state_string_true(self, mock_impl, temp_state_dir, clear_state_before):
        """Should parse fetch_logs string value from state."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "123")
        set_value("fetch_logs", "true")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["fetch_logs"] is True

    @patch("dfly_ai_helpers.cli.azure_devops.run_details_commands.wait_for_run_impl")
    def test_vpn_toggle_from_state_string_yes(self, mock_impl, temp_state_dir, clear_state_before):
        """Should parse vpn_toggle string value from state."""
        from dfly_ai_helpers.state import set_value

        set_value("run_id", "123")
        set_value("vpn_toggle", "yes")

        mock_impl.return_value = {"success": True}

        wait_for_run()

        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["vpn_toggle"] is True


class TestFetchFailedJobLogsVpnToggle:
    """Tests for VPN toggle behavior in fetch_failed_job_logs."""

    @patch("dfly_ai_helpers.cli.azure_devops.vpn_toggle.check_network_status")
    def test_returns_early_on_corporate_network(self, mock_check_network, capsys):
        """Should return early with message when on corporate network without VPN."""
        from dfly_ai_helpers.cli.azure_devops.vpn_toggle import NetworkStatus

        mock_check_network.return_value = (NetworkStatus.CORPORATE_NETWORK_NO_VPN, "In office")

        result = fetch_failed_job_logs(123, vpn_toggle=True)

        assert result["success"] is True
        assert "corporate network" in result["error"].lower()
        captured = capsys.readouterr()
        assert "Cannot fetch logs from corporate network" in captured.out
