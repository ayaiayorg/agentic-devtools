"""
Tests for role_commands module - Jira project role management.
"""


class TestCheckUserExistsCommand:
    """Tests for check_user_exists CLI command."""

    def test_prints_error_when_username_not_set(self, capsys):
        """Test prints error when username not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import check_user_exists

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value=None):
            check_user_exists()

        captured = capsys.readouterr()
        assert "Error: username not set" in captured.out

    def test_prints_success_for_active_user(self, capsys):
        """Test prints success message for active user."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import check_user_exists

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True, "displayName": "Test User"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value="test.user"):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            check_user_exists()

        captured = capsys.readouterr()
        assert "✓ User exists" in captured.out

    def test_prints_warning_for_inactive_user(self, capsys):
        """Test prints warning for inactive user."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import check_user_exists

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": False, "displayName": "Inactive User"}

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
                            check_user_exists()

        captured = capsys.readouterr()
        assert "inactive" in captured.out.lower()
