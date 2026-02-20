"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestCheckUsersExistCommandPaths:
    """Additional tests for check_users_exist command to cover more paths."""

    def test_handles_inactive_user(self, capsys, tmp_path):
        """Test handling of inactive user in check_users_exist."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import check_users_exist

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": False, "displayName": "Inactive User (INACTIVE)"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value="inactive.user"):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            with patch("agdt_ai_helpers.cli.jira.role_commands.TEMP_DIR", str(tmp_path)):
                                check_users_exist()

        captured = capsys.readouterr()
        assert "⚠" in captured.out or "inactive" in captured.out.lower()

    def test_handles_nonexistent_user(self, capsys):
        """Test handling of non-existent user in check_users_exist."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import check_users_exist

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value="nonexistent.user"):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            check_users_exist()

        captured = capsys.readouterr()
        assert "NOT FOUND" in captured.out
