"""Tests for fetch_threads_lookup function."""

from unittest.mock import MagicMock

from agentic_devtools.cli.azure_devops.suggestion_verification import fetch_threads_lookup


class TestFetchThreadsLookup:
    """Tests for fetch_threads_lookup."""

    def test_success_builds_lookup(self):
        """Successful API call returns thread_id → thread_data mapping."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": 1, "status": "active", "comments": [{"id": 1}]},
                {"id": 2, "status": "closed", "comments": [{"id": 1}, {"id": 2}]},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = fetch_threads_lookup(mock_requests, {"Authorization": "Bearer x"}, "https://example.com/threads")
        assert result is not None
        assert 1 in result
        assert 2 in result
        assert result[1]["status"] == "active"
        assert result[2]["status"] == "closed"

    def test_api_failure_returns_none(self):
        """API failure returns None (don't block on errors)."""
        mock_requests = MagicMock()
        mock_requests.get.side_effect = Exception("Network error")

        result = fetch_threads_lookup(mock_requests, {}, "https://example.com/threads")
        assert result is None

    def test_empty_threads_list(self):
        """Empty threads list returns empty dict."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"value": []}
        mock_response.raise_for_status = MagicMock()
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = fetch_threads_lookup(mock_requests, {}, "https://example.com/threads")
        assert result == {}

    def test_threads_without_id_skipped(self):
        """Threads without 'id' field are skipped."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "value": [
                {"id": 1, "status": "active"},
                {"status": "active"},  # missing id
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = fetch_threads_lookup(mock_requests, {}, "https://example.com/threads")
        assert len(result) == 1
        assert 1 in result
