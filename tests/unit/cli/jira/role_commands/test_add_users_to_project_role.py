"""
Tests for role_commands module - Jira project role management.
"""


class TestAddUsersToProjectRole:
    """Tests for add_users_to_project_role CLI command."""

    def test_prints_error_when_project_not_set(self, capsys):
        """Test prints error when project_id_or_key not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value=None):
            add_users_to_project_role()

        captured = capsys.readouterr()
        assert "Error: project_id_or_key not set" in captured.out

    def test_prints_success_on_200_response(self, capsys):
        """Test prints success message on 200 response."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "Developers", "actors": [{"id": 1}, {"id": 2}]}

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        def mock_get_jira_value(key):
            if key == "project_id_or_key":
                return "PROJ"
            if key == "role_id":
                return "10100"
            if key == "users":
                return "user1,user2"
            return None

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
        assert "Successfully added users" in captured.out

    def test_prints_error_on_400_response(self, capsys):
        """Test prints error on 400 Bad Request response."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid user"

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        def mock_get_jira_value(key):
            if key == "project_id_or_key":
                return "PROJ"
            if key == "role_id":
                return "10100"
            if key == "users":
                return "invalid_user"
            return None

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
        assert "Bad Request" in captured.out
