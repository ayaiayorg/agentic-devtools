"""Tests for _fetch_threads function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.finalization.orchestrator import _fetch_threads


def _mock_config():
    config = MagicMock()
    config.build_api_url.return_value = "https://api/threads"
    return config


class TestFetchThreads:
    """Tests for _fetch_threads function."""

    def test_returns_threads_on_success(self):
        """Should return thread list on successful API call."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": [{"id": 1}, {"id": 2}]}
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = _fetch_threads(_mock_config(), {}, "repo-guid", 42)

        assert result == [{"id": 1}, {"id": 2}]

    def test_returns_none_on_exception(self):
        """Should return None when API call fails."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("connection error")

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = _fetch_threads(_mock_config(), {}, "repo-guid", 42)

        assert result is None

    def test_returns_none_on_http_error(self):
        """Should return None when API returns an HTTP error."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_requests.get.return_value = mock_response

        with patch(
            "agentic_devtools.cli.azure_devops.helpers.require_requests",
            return_value=mock_requests,
        ):
            result = _fetch_threads(_mock_config(), {}, "repo-guid", 42)

        assert result is None
