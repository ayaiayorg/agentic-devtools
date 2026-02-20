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
