"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestGetProjectRoleDetailsCommandPaths:
    """Tests for get_project_role_details command covering more branches."""

    def test_prints_error_when_role_id_not_set(self, capsys):
        """Test error when role_id not set."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            get_project_role_details()

        captured = capsys.readouterr()
        assert "Error: role_id not set" in captured.out

    def test_prints_error_on_api_failure(self, capsys):
        """Test error message on API failure."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "99999"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            get_project_role_details()

        captured = capsys.readouterr()
        assert "Error: Failed to get role details" in captured.out

    def test_displays_role_with_no_actors(self, capsys):
        """Test display when role has no actors."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 10100,
            "name": "Empty Role",
            "description": "A role with no members",
            "actors": [],
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            get_project_role_details()

        captured = capsys.readouterr()
        assert "Empty Role" in captured.out
        assert "No actors assigned" in captured.out

    def test_displays_role_with_users_and_groups(self, capsys):
        """Test display when role has both user and group actors."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 10100,
            "name": "Dev Team",
            "description": "Development team",
            "actors": [
                {"type": "atlassian-user-role-actor", "displayName": "John Doe", "name": "john.doe"},
                {"type": "atlassian-group-role-actor", "displayName": "developers", "name": "developers"},
            ],
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            get_project_role_details()

        captured = capsys.readouterr()
        assert "Dev Team" in captured.out
        assert "Users (1)" in captured.out
        assert "John Doe" in captured.out
        assert "Groups (1)" in captured.out
        assert "developers" in captured.out
