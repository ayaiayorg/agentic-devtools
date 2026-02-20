"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge

from agdt_ai_helpers.cli.jira.parse_error_report import (
    _parse_error_file,
)


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
