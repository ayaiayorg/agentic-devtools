"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestListProjectRoles:
    """Tests for list_project_roles CLI command."""

    def test_prints_error_when_project_not_set(self, capsys):
        """Test prints error when project_id_or_key not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import list_project_roles

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value=None):
            list_project_roles()

        captured = capsys.readouterr()
        assert "Error: project_id_or_key not set" in captured.out

    def test_prints_roles_on_success(self, capsys):
        """Test prints roles table on success."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import list_project_roles

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Developers": "https://jira.example.com/rest/api/2/project/KEY/role/10100",
            "Administrators": "https://jira.example.com/rest/api/2/project/KEY/role/10200",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value="PROJ"):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            list_project_roles()

        captured = capsys.readouterr()
        assert "Developers" in captured.out
        assert "Administrators" in captured.out
        assert "10100" in captured.out
        assert "Total: 2 roles" in captured.out

    def test_prints_error_on_api_failure(self, capsys):
        """Test prints error on API failure."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import list_project_roles

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Project not found"

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value="INVALID"):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            list_project_roles()

        captured = capsys.readouterr()
        assert "Error: Failed to get project roles" in captured.out
