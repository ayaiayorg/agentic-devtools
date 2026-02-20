"""
Tests for role_commands module - Jira project role management.
"""


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
