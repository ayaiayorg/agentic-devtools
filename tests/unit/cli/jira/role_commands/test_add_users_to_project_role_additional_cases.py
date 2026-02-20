"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestAddUsersToProjectRoleAdditionalCases:
    """Additional tests for add_users_to_project_role command error paths."""

    def test_prints_error_on_401_response(self, capsys):
        """Test prints error on 401 Unauthorized response."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "user1"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            add_users_to_project_role()

        captured = capsys.readouterr()
        assert "Unauthorized" in captured.out

    def test_prints_error_on_404_response(self, capsys):
        """Test prints error on 404 Not Found response."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Project not found"

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "INVALID", "role_id": "10100", "users": "user1"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            add_users_to_project_role()

        captured = capsys.readouterr()
        assert "Not Found" in captured.out

    def test_prints_error_on_unknown_status(self, capsys):
        """Test prints error on unexpected status code."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "user1"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            add_users_to_project_role()

        captured = capsys.readouterr()
        assert "Error: Status 500" in captured.out

    def test_error_when_users_empty_after_parse(self, capsys):
        """Test error when users parses to empty list."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "   ,  ,  "}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            add_users_to_project_role()

        captured = capsys.readouterr()
        assert "No valid usernames" in captured.out
