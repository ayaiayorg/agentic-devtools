"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge


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
