"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge

from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.parse_error_report import (
    _get_user_details,
    _parse_error_file,
)


class TestGetUserDetailsApiCalls:
    """Tests for _get_user_details API call handling."""

    def test_correct_url_construction(self):
        """Test URL is constructed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        called_url = mock_requests.get.call_args[0][0]
        assert called_url == "https://jira.example.com/rest/api/2/user?username=test.user"

    def test_ssl_verify_passed_correctly(self):
        """Test ssl_verify parameter is passed to requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=False,
        )

        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["verify"] is False

    def test_handles_server_error(self):
        """Test handles 500 server error gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is False
        assert result["active"] is False
