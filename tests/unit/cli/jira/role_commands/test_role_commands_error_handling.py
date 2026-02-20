"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestRoleCommandsErrorHandling:
    """Tests for error handling in role commands."""

    def test_user_check_handles_401(self):
        """Test handling 401 Unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="any.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        # 401 should be treated as user not found
        assert exists is False
        assert display_name is None

    def test_user_check_handles_500(self):
        """Test handling 500 Internal Server Error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="any.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        # 500 should be treated as user not found
        assert exists is False
        assert display_name is None
