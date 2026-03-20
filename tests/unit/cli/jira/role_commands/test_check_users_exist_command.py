"""
Tests for role_commands module - Jira project role management.
"""


class TestCheckUsersExistCommand:
    """Tests for check_users_exist CLI command."""

    def test_prints_error_when_users_not_set(self, capsys):
        """Test prints error when users not in state."""
        from unittest.mock import patch

        from agentic_devtools.cli.jira.role_commands import check_users_exist

        with patch("agentic_devtools.cli.jira.role_commands.get_jira_value", return_value=None):
            check_users_exist()

        captured = capsys.readouterr()
        assert "Error: users not set" in captured.out

    def test_prints_error_for_empty_users(self, capsys):
        """Test prints error for empty users list."""
        from unittest.mock import patch

        from agentic_devtools.cli.jira.role_commands import check_users_exist

        with patch("agentic_devtools.cli.jira.role_commands.get_jira_value", return_value=""):
            check_users_exist()

        captured = capsys.readouterr()
        assert "Error" in captured.out
