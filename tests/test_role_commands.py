"""
Tests for role_commands module - Jira project role management.
"""

import re
from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.role_commands import (
    _check_user_exists,
)


class TestCheckUserExists:
    """Tests for _check_user_exists function."""

    def test_user_exists_and_active(self):
        """Test checking active user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            "displayName": "John Doe",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="john.doe",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is True
        assert display_name == "John Doe"

    def test_user_exists_but_inactive(self):
        """Test checking inactive user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": False,
            "displayName": "Inactive User",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="inactive.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is False
        assert "(INACTIVE)" in display_name
        assert "Inactive User" in display_name

    def test_user_not_found(self):
        """Test checking non-existent user."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="nonexistent",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is False
        assert display_name is None

    def test_user_without_display_name(self):
        """Test user response without displayName field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            # No displayName field
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="minimal.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert exists is True
        # Falls back to username
        assert display_name == "minimal.user"

    def test_api_url_construction(self):
        """Test that API URL is correctly constructed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True, "displayName": "Test"}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _check_user_exists(
            username="test.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        called_url = mock_requests.get.call_args[0][0]
        assert called_url == "https://jira.example.com/rest/api/2/user?username=test.user"

    def test_ssl_verify_passed(self):
        """Test that ssl_verify parameter is passed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _check_user_exists(
            username="test.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=False,
        )

        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["verify"] is False


class TestRoleIdExtraction:
    """Tests for role ID extraction from URLs."""

    def test_extract_role_id_from_url(self):
        """Test extracting role ID from Jira role URL."""
        role_url = "https://jira.example.com/rest/api/2/project/PROJ/role/12345"
        pattern = re.compile(r"/role/(\d+)$")
        match = pattern.search(role_url)

        assert match is not None
        assert match.group(1) == "12345"

    def test_extract_role_id_different_numbers(self):
        """Test extracting various role IDs."""
        test_cases = [
            ("https://jira.example.com/rest/api/2/project/KEY/role/10100", "10100"),
            ("https://jira.example.com/rest/api/2/project/KEY/role/99999", "99999"),
            ("https://jira.example.com/rest/api/2/project/KEY/role/1", "1"),
        ]

        pattern = re.compile(r"/role/(\d+)$")
        for url, expected_id in test_cases:
            match = pattern.search(url)
            assert match is not None
            assert match.group(1) == expected_id

    def test_no_role_id_in_url(self):
        """Test URL without role ID."""
        url = "https://jira.example.com/rest/api/2/project/KEY"
        pattern = re.compile(r"/role/(\d+)$")
        match = pattern.search(url)

        assert match is None


class TestRoleCommandsErrorHandling:
    """Tests for error handling in role commands."""

    def test_user_check_handles_401(self):
        """Test handling 401 Unauthorized."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="any.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        # 401 should be treated as user not found
        assert exists is False
        assert display_name is None

    def test_user_check_handles_500(self):
        """Test handling 500 Internal Server Error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        exists, display_name = _check_user_exists(
            username="any.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        # 500 should be treated as user not found
        assert exists is False
        assert display_name is None


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


class TestCheckUsersExistCommand:
    """Tests for check_users_exist CLI command."""

    def test_prints_error_when_users_not_set(self, capsys):
        """Test prints error when users not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import check_users_exist

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value=None):
            check_users_exist()

        captured = capsys.readouterr()
        assert "Error: users not set" in captured.out

    def test_prints_error_for_empty_users(self, capsys):
        """Test prints error for empty users list."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import check_users_exist

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value=""):
            check_users_exist()

        captured = capsys.readouterr()
        assert "Error" in captured.out


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


class TestCheckUsersExistCommandPaths:
    """Additional tests for check_users_exist command to cover more paths."""

    def test_handles_inactive_user(self, capsys, tmp_path):
        """Test handling of inactive user in check_users_exist."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import check_users_exist

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": False, "displayName": "Inactive User (INACTIVE)"}

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
                            with patch("agdt_ai_helpers.cli.jira.role_commands.TEMP_DIR", str(tmp_path)):
                                check_users_exist()

        captured = capsys.readouterr()
        assert "⚠" in captured.out or "inactive" in captured.out.lower()

    def test_handles_nonexistent_user(self, capsys):
        """Test handling of non-existent user in check_users_exist."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import check_users_exist

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", return_value="nonexistent.user"):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            check_users_exist()

        captured = capsys.readouterr()
        assert "NOT FOUND" in captured.out


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


class TestFindRoleIdByName:
    """Tests for find_role_id_by_name CLI command."""

    def test_prints_error_when_project_not_set(self, capsys):
        """Test prints error when project_id_or_key not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import find_role_id_by_name

        def mock_get_jira_value(key):
            return None

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            find_role_id_by_name()

        captured = capsys.readouterr()
        assert "Error: project_id_or_key not set" in captured.out

    def test_prints_error_when_role_name_not_set(self, capsys):
        """Test prints error when role_name not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.role_commands import find_role_id_by_name

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            find_role_id_by_name()

        captured = capsys.readouterr()
        assert "Error: role_name not set" in captured.out

    def test_finds_single_match(self, capsys):
        """Test finding a single matching role."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import find_role_id_by_name

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Developers": "https://jira.example.com/rest/api/2/project/KEY/role/10100",
            "Administrators": "https://jira.example.com/rest/api/2/project/KEY/role/10200",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_name": "Developers"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            find_role_id_by_name()

        captured = capsys.readouterr()
        assert "Found role: Developers" in captured.out
        assert "Role ID: 10100" in captured.out

    def test_finds_multiple_matches(self, capsys):
        """Test finding multiple matching roles."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import find_role_id_by_name

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Dev Team A": "https://jira.example.com/rest/api/2/project/KEY/role/10100",
            "Dev Team B": "https://jira.example.com/rest/api/2/project/KEY/role/10200",
            "Administrators": "https://jira.example.com/rest/api/2/project/KEY/role/10300",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_name": "Dev"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            find_role_id_by_name()

        captured = capsys.readouterr()
        assert "Multiple roles match" in captured.out
        assert "Dev Team A" in captured.out
        assert "Dev Team B" in captured.out

    def test_no_matches_found(self, capsys):
        """Test when no roles match the search."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import find_role_id_by_name

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "Administrators": "https://jira.example.com/rest/api/2/project/KEY/role/10100",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_name": "NonExistent"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            find_role_id_by_name()

        captured = capsys.readouterr()
        assert "No roles found matching" in captured.out
        assert "Available roles" in captured.out

    def test_api_failure(self, capsys):
        """Test handling of API failure."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.role_commands import find_role_id_by_name

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        def mock_get_jira_value(key):
            return {"project_id_or_key": "PROJ", "role_name": "Developers"}.get(key)

        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_value", side_effect=mock_get_jira_value):
            with patch("agdt_ai_helpers.cli.jira.role_commands._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.role_commands._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.role_commands.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.role_commands.get_jira_headers", return_value={}):
                            find_role_id_by_name()

        captured = capsys.readouterr()
        assert "Error: Failed to get project roles" in captured.out
