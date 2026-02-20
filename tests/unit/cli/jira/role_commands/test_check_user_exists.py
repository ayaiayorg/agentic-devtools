"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestCheckUserExists:
    """Tests for _check_user_exists function."""

    def test_user_exists_and_active(self):
        """Test checking active user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            "displayName": "John Doe",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="john.doe",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is True
        assert display_name == "John Doe"

    def test_user_exists_but_inactive(self):
        """Test checking inactive user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": False,
            "displayName": "Inactive User",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="inactive.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is False
        assert "(INACTIVE)" in display_name
        assert "Inactive User" in display_name

    def test_user_not_found(self):
        """Test checking non-existent user."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="nonexistent",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is False
        assert display_name is None

    def test_user_without_display_name(self):
        """Test user response without displayName field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            # No displayName field
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="minimal.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is True
        # Falls back to username
        assert display_name == "minimal.user"

    def test_api_url_construction(self):
        """Test that API URL is correctly constructed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True, "displayName": "Test"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _check_user_exists(
            username="test.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        called_url = mock_requests.get.call_args[0][0]
        assert called_url == "https://jira.example.com/rest/api/2/user?username=test.user"

    def test_ssl_verify_passed(self):
        """Test that ssl_verify parameter is passed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _check_user_exists(
            username="test.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=False,
        )

        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["verify"] is False
