"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge

from unittest.mock import MagicMock

from agdt_ai_helpers.cli.jira.parse_error_report import (
    _get_user_details,
    _parse_error_file,
)


class TestParseErrorFile:
    """Tests for _parse_error_file function."""

    def test_parse_assignee_cannot_be_assigned(self, tmp_path):
        """Test parsing error for user who cannot be assigned.

        Note: The function applies unicode_escape decode, so German umlauts
        must be written as unicode escapes in the test data (e.g., \\u00f6 for ö).
        """
        # The function uses a regex that expects a specific format:
        # "errorMessage": "..." followed by "issues": [...] with customfield_16100 (Externe Referenz): value
        # Use unicode escapes for umlauts since the code does unicode_escape decode
        error_content = """
"errorMessage": "Benutzer 'john.doe' k\\u00f6nnen keine Vorg\\u00e4nge zugewiesen werden."
"issues": [
    customfield_16100 (Externe Referenz): dp-test-product
]
"""
        file_path = tmp_path / "error.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert len(results) == 1
        assert results[0]["username"] == "john.doe"
        assert results[0]["role"] == "assignee"
        assert results[0]["dataproduct"] == "dp-test-product"
        assert results[0]["errorType"] == "cannot_be_assigned"

    def test_parse_user_not_found(self, tmp_path):
        """Test parsing error for user that doesn't exist."""
        error_content = """
"errorMessage": "Der Benutzer 'jane.smith' existiert nicht."
"issues": [
    customfield_16100 (Externe Referenz): dp-another-product
]
"""
        file_path = tmp_path / "error.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert len(results) == 1
        assert results[0]["username"] == "jane.smith"
        assert results[0]["role"] == "assignee"
        assert results[0]["errorType"] == "not_found"

    def test_parse_reporter_error(self, tmp_path):
        """Test parsing error for reporter issues."""
        error_content = """
"errorMessage": "Der angegebene Autor ist kein Benutzer."
"issues": [
    customfield_16100 (Externe Referenz): dp-reporter-product
]
"""
        file_path = tmp_path / "error.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert len(results) == 1
        assert results[0]["username"] == "(unknown - reporter error)"
        assert results[0]["role"] == "reporter"
        assert results[0]["errorType"] == "not_a_user"

    def test_parse_empty_file(self, tmp_path):
        """Test parsing empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_text("", encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert results == []

    def test_parse_no_matching_errors(self, tmp_path):
        """Test parsing file with no matching error patterns."""
        error_content = "Some random content without errors"
        file_path = tmp_path / "noerror.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert results == []

    def test_parse_multiple_errors(self, tmp_path):
        """Test parsing file with multiple errors.

        Note: Use unicode escapes for umlauts and curly braces to separate blocks.
        """
        error_content = """
{
"errorMessage": "Benutzer 'user1' k\\u00f6nnen keine Vorg\\u00e4nge zugewiesen werden."
"issues": [
    customfield_16100 (Externe Referenz): dp-product-1
]
}

{
"errorMessage": "Der Benutzer 'user2' existiert nicht."
"issues": [
    customfield_16100 (Externe Referenz): dp-product-2
]
}
"""
        file_path = tmp_path / "errors.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert len(results) == 2

    def test_parse_multiple_dataproducts_in_one_error(self, tmp_path):
        """Test parsing error with multiple dataproducts.

        Note: Use unicode escapes for umlauts.
        """
        error_content = """
{
"errorMessage": "Benutzer 'user1' k\\u00f6nnen keine Vorg\\u00e4nge zugewiesen werden."
"issues": [
    customfield_16100 (Externe Referenz): dp-product-1,
    customfield_16100 (Externe Referenz): dp-product-2
]
}
"""
        file_path = tmp_path / "errors.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        # Should create separate entries for each dataproduct
        assert len(results) == 2
        dataproducts = [r["dataproduct"] for r in results]
        assert "dp-product-1" in dataproducts
        assert "dp-product-2" in dataproducts

    def test_parse_unicode_escaped_content(self, tmp_path):
        """Test parsing file with unicode escapes."""
        # The code decodes unicode escapes, so \u0027 becomes '
        error_content = """
"errorMessage": "Benutzer \\u0027user.one\\u0027 k\\u00f6nnen keine Vorg\\u00e4nge zugewiesen werden."
"issues": [
    customfield_16100 (Externe Referenz): dp-unicode-test
]
"""
        file_path = tmp_path / "unicode.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        # Unicode escapes should be decoded
        assert len(results) == 1
        assert results[0]["username"] == "user.one"


class TestGetUserDetails:
    """Tests for _get_user_details function."""

    def test_user_exists_and_active(self):
        """Test getting details for existing active user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            "displayName": "John Doe",
            "emailAddress": "john.doe@example.com",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="john.doe",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is True
        assert result["active"] is True
        assert result["displayName"] == "John Doe"
        assert result["emailAddress"] == "john.doe@example.com"

    def test_user_exists_but_inactive(self):
        """Test getting details for existing inactive user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": False,
            "displayName": "Inactive User",
            "emailAddress": "inactive@example.com",
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="inactive.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is True
        assert result["active"] is False
        assert result["displayName"] == "Inactive User"

    def test_user_not_found(self):
        """Test getting details for non-existent user."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="nonexistent",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is False
        assert result["active"] is False
        assert result["displayName"] == ""
        assert result["emailAddress"] == ""

    def test_api_url_format(self):
        """Test that API URL is correctly formatted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        # Verify the URL was constructed correctly
        called_url = mock_requests.get.call_args[0][0]
        assert called_url == "https://jira.example.com/rest/api/2/user?username=test.user"

    def test_user_with_missing_fields(self):
        """Test handling user response with missing optional fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # Only 'active' field, missing displayName and emailAddress
            "active": True,
        }

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="minimal.user",
            base_url="https://jira.example.com",
            headers={"Authorization": "Basic xxx"},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is True
        assert result["active"] is True
        assert result["displayName"] == ""
        assert result["emailAddress"] == ""


class TestParseJiraErrorReportIntegration:
    """Integration-style tests for parse_jira_error_report."""

    def test_end_to_end_parsing(self, tmp_path):
        """Test complete parsing workflow with realistic data.

        Note: Use unicode escapes for umlauts since the function applies unicode_escape decode.
        """
        # Create a realistic error file with unicode escapes
        error_content = """
"errorMessage": "Benutzer 'user.one' k\\u00f6nnen keine Vorg\\u00e4nge zugewiesen werden."
"issues": [
    customfield_16100 (Externe Referenz): dp-data-product-alpha
]
"""
        file_path = tmp_path / "realistic_error.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        assert len(results) == 1
        assert results[0]["username"] == "user.one"
        assert results[0]["dataproduct"] == "dp-data-product-alpha"


class TestParseJiraErrorReportCommand:
    """Tests for parse_jira_error_report CLI command."""

    def test_prints_error_when_file_path_not_set(self, capsys):
        """Test prints error when error_file_path not in state."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.parse_error_report import parse_jira_error_report

        with patch("agdt_ai_helpers.cli.jira.parse_error_report.get_jira_value", return_value=None):
            parse_jira_error_report()

        captured = capsys.readouterr()
        assert "Error: error_file_path not set" in captured.out

    def test_prints_error_when_file_not_found(self, capsys):
        """Test prints error when file doesn't exist."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.parse_error_report import parse_jira_error_report

        with patch("agdt_ai_helpers.cli.jira.parse_error_report.get_jira_value", return_value="/nonexistent/path.txt"):
            parse_jira_error_report()

        captured = capsys.readouterr()
        assert "Error: File not found" in captured.out

    def test_prints_no_entries_for_empty_file(self, tmp_path, capsys):
        """Test prints message when no entries found."""
        from unittest.mock import patch

        from agdt_ai_helpers.cli.jira.parse_error_report import parse_jira_error_report

        # Create empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        with patch("agdt_ai_helpers.cli.jira.parse_error_report.get_jira_value", return_value=str(empty_file)):
            parse_jira_error_report()

        captured = capsys.readouterr()
        assert "No error entries found" in captured.out

    def test_parses_and_outputs_report(self, tmp_path, capsys):
        """Test full parsing and output generation."""
        from unittest.mock import MagicMock, patch

        from agdt_ai_helpers.cli.jira.parse_error_report import parse_jira_error_report

        # Create test error file with unicode escapes
        error_content = """
"errorMessage": "Der Benutzer 'test.user' existiert nicht."
"issues": [
    customfield_16100 (Externe Referenz): dp-test-product
]
"""
        error_file = tmp_path / "errors.txt"
        error_file.write_text(error_content, encoding="utf-8")

        # Mock the Jira API to return not found for user lookup
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        # Patch TEMP_DIR to use tmp_path
        with patch("agdt_ai_helpers.cli.jira.parse_error_report.get_jira_value", return_value=str(error_file)):
            with patch("agdt_ai_helpers.cli.jira.parse_error_report._get_requests", return_value=mock_requests):
                with patch("agdt_ai_helpers.cli.jira.parse_error_report._get_ssl_verify", return_value=True):
                    with patch(
                        "agdt_ai_helpers.cli.jira.parse_error_report.get_jira_base_url",
                        return_value="https://jira.example.com",
                    ):
                        with patch("agdt_ai_helpers.cli.jira.parse_error_report.get_jira_headers", return_value={}):
                            with patch("agdt_ai_helpers.cli.jira.parse_error_report.TEMP_DIR", str(tmp_path)):
                                parse_jira_error_report()

        captured = capsys.readouterr()
        assert "Found 1 error entries" in captured.out
        assert "test.user" in captured.out


class TestParseErrorFileMultipleDataproducts:
    """Tests for parsing errors with multiple dataproducts."""

    def test_parse_multiple_dataproducts_same_error(self, tmp_path):
        """Test parsing error affecting multiple dataproducts."""
        error_content = """
"errorMessage": "Der Benutzer 'multi.user' existiert nicht."
"issues": [
    customfield_16100 (Externe Referenz): dp-product-one,
    customfield_16100 (Externe Referenz): dp-product-two
]
"""
        file_path = tmp_path / "multi.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        # Should have entries for each dataproduct
        assert len(results) == 2
        assert all(r["username"] == "multi.user" for r in results)
        dataproducts = {r["dataproduct"] for r in results}
        assert "dp-product-one" in dataproducts
        assert "dp-product-two" in dataproducts


class TestParseErrorFileCombinedErrors:
    """Tests for parsing files with both assignee and reporter errors."""

    def test_parse_combined_assignee_and_reporter(self, tmp_path):
        """Test parsing error with both assignee and reporter issues.

        Note: Use unicode escapes for umlauts.
        """
        error_content = """
"errorMessage": "Benutzer 'assignee.user' k\\u00f6nnen keine Vorg\\u00e4nge zugewiesen werden. \
Der angegebene Autor ist kein Benutzer."
"issues": [
    customfield_16100 (Externe Referenz): dp-combined-product
]
"""
        file_path = tmp_path / "combined.txt"
        file_path.write_text(error_content, encoding="utf-8")

        results = _parse_error_file(str(file_path))

        # Should have both assignee and reporter entries
        assert len(results) == 2
        roles = {r["role"] for r in results}
        assert "assignee" in roles
        assert "reporter" in roles


class TestGetUserDetailsApiCalls:
    """Tests for _get_user_details API call handling."""

    def test_correct_url_construction(self):
        """Test URL is constructed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        called_url = mock_requests.get.call_args[0][0]
        assert called_url == "https://jira.example.com/rest/api/2/user?username=test.user"

    def test_ssl_verify_passed_correctly(self):
        """Test ssl_verify parameter is passed to requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": True}

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=False,
        )

        call_kwargs = mock_requests.get.call_args[1]
        assert call_kwargs["verify"] is False

    def test_handles_server_error(self):
        """Test handles 500 server error gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response

        result = _get_user_details(
            username="test.user",
            base_url="https://jira.example.com",
            headers={},
            requests=mock_requests,
            ssl_verify=True,
        )

        assert result["exists"] is False
        assert result["active"] is False
