"""
Tests for run_details_commands module.
"""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops import get_run_details
from agentic_devtools.cli.azure_devops.run_details_commands import (
    get_run_details_impl,
)


class TestGetRunDetails:
    """Tests for get_run_details CLI command."""

    def test_dry_run_output(self, temp_state_dir, clear_state_before, capsys):
        """Should show dry run output when dry_run is set."""
        from agentic_devtools.state import set_value

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
        from agentic_devtools.state import set_value

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
        from agentic_devtools.state import set_value

        set_value("run_id", "not-a-number")

        with pytest.raises(SystemExit) as exc_info:
            get_run_details()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "integer" in captured.err

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    def test_api_failure_exits_with_error(
        self, mock_get_pat, mock_require_requests, temp_state_dir, clear_state_before
    ):
        """Should exit with code 1 when API calls fail."""
        from agentic_devtools.state import set_value

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

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._save_json")
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

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._save_json")
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

    @patch("agentic_devtools.cli.azure_devops.run_details_commands.require_requests")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands.get_pat")
    @patch("agentic_devtools.cli.azure_devops.run_details_commands._save_json")
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
