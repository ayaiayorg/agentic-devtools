"""
Tests for run_details_commands module.
"""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.run_details_commands import (
    _fetch_build_timeline,
)


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
