"""
Tests for run_details_commands module.
"""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.run_details_commands import (
    _fetch_task_log,
)


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
