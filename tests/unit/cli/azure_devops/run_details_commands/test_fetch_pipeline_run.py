"""
Tests for run_details_commands module.
"""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.run_details_commands import (
    _fetch_pipeline_run,
)


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
