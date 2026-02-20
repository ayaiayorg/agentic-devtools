"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestAddUsersToProjectRoleBatch:
    """Tests for add_users_to_project_role_batch CLI command."""

    def test_prints_error_when_project_not_set(self, capsys):
        """Test prints error when project_id_or_key not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        def mock_get_jira_value(key):
            return None

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "Error: project_id_or_key not set" in captured.out

    def test_prints_error_when_role_not_set(self, capsys):
        """Test prints error when role_id not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "Error: role_id not set" in captured.out

    def test_prints_error_when_users_not_set(self, capsys):
        """Test prints error when users not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "Error: users not set" in captured.out

    def test_prints_error_when_users_empty(self, capsys):
        """Test prints error when users parses to empty list."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "   ,  ,  "}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "No valid usernames" in captured.out

    def test_batch_adds_existing_users(self, capsys, tmp_path):
        """Test batch add with mix of existing and non-existing users."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        # Mock user existence check - first user exists, second doesn't
        def mock_user_response(url, *args, **kwargs):
            response = MagicMock()
            if "username=existing.user" in url:
                response.status_code = 200
                response.json.return_value = {"active": True, "displayName": "Existing User"}
            else:
                response.status_code = 404
            return response

        # Mock role add
        def mock_post(url, *args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            return response

        mock_requests = MagicMock()
        mock_requests.get.side_effect = mock_user_response
        mock_requests.post.side_effect = mock_post

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "existing.user,nonexistent.user"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            with patch("agdt_ai_helpers.cli.jira.role_commands.TEMP_DIR", str(tmp_path)):
                                add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "FINAL SUMMARY" in captured.out
        assert "Successfully added" in captured.out

    def test_batch_handles_no_valid_users(self, capsys, tmp_path):
        """Test batch add when no users exist."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        # Mock user existence check - all users don't exist
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "nonexistent1,nonexistent2"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            with patch("agdt_ai_helpers.cli.jira.role_commands.TEMP_DIR", str(tmp_path)):
                                add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "No valid users to add" in captured.out

    def test_batch_handles_add_failure(self, capsys, tmp_path):
        """Test batch add when role add fails for some users."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import add_users_to_project_role_batch

        # Mock user existence check - both users exist
        def mock_user_response(url, *args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"active": True, "displayName": "User"}
            return response

        # Mock role add - first succeeds, second fails
        call_count = [0]

        def mock_post(url, *args, **kwargs):
            response = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                response.status_code = 200
            else:
                response.status_code = 400
                response.text = "User already in role"
            return response

        mock_requests = MagicMock()
        mock_requests.get.side_effect = mock_user_response
        mock_requests.post.side_effect = mock_post

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_id": "10100", "users": "user1,user2"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            with patch("agdt_ai_helpers.cli.jira.role_commands.TEMP_DIR", str(tmp_path)):
                                add_users_to_project_role_batch()

        captured = capsys.readouterr()
        assert "Failed to add" in captured.out
