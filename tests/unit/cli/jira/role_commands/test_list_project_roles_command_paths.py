"""
Tests for role_commands module - Jira project role management.
"""


class TestListProjectRolesCommandPaths:
    """Tests for list_project_roles command covering more branches."""

    def test_prints_error_when_project_not_set(self, capsys):
        """Test error when project_id_or_key not set."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import list_project_roles

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value=None):
            list_project_roles()

        captured = capsys.readouterr()
        assert "Error: project_id_or_key not set" in captured.out

    def test_prints_error_on_api_failure(self, capsys):
        """Test error message on API failure."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import list_project_roles

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

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
        assert "Error: Failed to get project roles" in captured.out

    def test_lists_roles_successfully(self, capsys):
        """Test successful role listing."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import list_project_roles

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Administrators": "https://jira.example.com/rest/api/2/project/PROJ/role/10100",
            "Developers": "https://jira.example.com/rest/api/2/project/PROJ/role/10101",
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
        assert "Administrators" in captured.out
        assert "10100" in captured.out
        assert "Total: 2 roles" in captured.out
