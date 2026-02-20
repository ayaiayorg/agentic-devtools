"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge

from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.parse_error_report import (
    _get_user_details,
)


class TestGetUserDetails:
    """Tests for _get_user_details function."""

    def test_user_exists_and_active(self):
        """Test getting details for existing active user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            "displayName": "John Doe",
            "emailAddress": "john.doe@example.com",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="john.doe",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is True
        assert result["active"] is True
        assert result["displayName"] == "John Doe"
        assert result["emailAddress"] == "john.doe@example.com"

    def test_user_exists_but_inactive(self):
        """Test getting details for existing inactive user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": False,
            "displayName": "Inactive User",
            "emailAddress": "inactive@example.com",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="inactive.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is True
        assert result["active"] is False
        assert result["displayName"] == "Inactive User"

    def test_user_not_found(self):
        """Test getting details for non-existent user."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="nonexistent",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is False
        assert result["active"] is False
        assert result["displayName"] == ""
        assert result["emailAddress"] == ""

    def test_api_url_format(self):
        """Test that API URL is correctly formatted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        # Verify the URL was constructed correctly
        called_url = mock_requests.get.call_args[0][0]
        assert called_url == "https://jira.example.com/rest/api/2/user?username=test.user"

    def test_user_with_missing_fields(self):
        """Test handling user response with missing optional fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # Only 'active' field, missing displayName and emailAddress
            "active": True,
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="minimal.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is True
        assert result["active"] is True
        assert result["displayName"] == ""
        assert result["emailAddress"] == ""
