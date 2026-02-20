"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestGetProjectRoleDetails:
    """Tests for get_project_role_details CLI command."""

    def test_prints_error_when_project_not_set(self, capsys):
        """Test prints error when project_id_or_key not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        def mock_get_jira_value(key):
            return None

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            get_project_role_details()

        captured = capsys.readouterr()
        assert "Error: project_id_or_key not set" in captured.out

    def test_prints_error_when_role_not_set(self, capsys):
        """Test prints error when role_id not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        def mock_get_jira_value(key):
            if key == "project_id_or_key":
                return "PROJ"
            return None

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            get_project_role_details()

        captured = capsys.readouterr()
        assert "Error: role_id not set" in captured.out

    def test_prints_role_details_on_success(self, capsys):
        """Test prints role details on success."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import get_project_role_details

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Developers",
            "id": 10100,
            "description": "Developer access",
            "actors": [
                {
                    "type": "atlassian-user-role-actor",
                    "displayName": "Albert Marsnik",
                    "actorUser": {"name": "amarsnik"},
                },
                {
                    "type": "atlassian-group-role-actor",
                    "displayName": "Developer Group",
                    "actorGroup": {"name": "developerGroup"},
                },
            ],
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            if key == "project_id_or_key":
                return "PROJ"
            if key == "role_id":
                return "10100"
            return None

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
        assert "Developers" in captured.out
        assert "Albert Marsnik" in captured.out
        assert "Developer Group" in captured.out
