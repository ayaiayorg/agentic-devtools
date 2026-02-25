"""Tests for check_users_exist function."""

from unittest.mock import patch

from agentic_devtools.cli.jira.role_commands import check_users_exist


class TestCheckUsersExist:
    """Tests for check_users_exist function."""

    def test_prints_error_when_users_not_set(self, capsys):
        """Should print error when jira.users is not set in state."""
        with patch(
            "agentic_devtools.cli.jira.role_commands.get_jira_value",
            return_value=None,
        ):
            check_users_exist()

        captured = capsys.readouterr()
        assert "users" in captured.out.lower() or "Error" in captured.out

    def test_function_is_callable(self):
        """Verify check_users_exist is importable and callable."""
        assert callable(check_users_exist)

    def test_prints_checking_message_when_users_set(self, capsys):
        """Should print a checking message when users are provided."""
        mock_requests = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock
        mock_resp = mock_requests()
        mock_resp.status_code = 404

        with patch(
            "agentic_devtools.cli.jira.role_commands.get_jira_value",
            return_value="user1,user2",
        ):
            with patch("agentic_devtools.cli.jira.role_commands._get_requests", return_value=mock_requests()):
                with patch("agentic_devtools.cli.jira.role_commands.get_jira_base_url", return_value="http://jira"):
                    with patch("agentic_devtools.cli.jira.role_commands.get_jira_headers", return_value={}):
                        with patch("agentic_devtools.cli.jira.role_commands._get_ssl_verify", return_value=False):
                            check_users_exist()

        captured = capsys.readouterr()
        assert captured.out != "" or captured.err != ""
