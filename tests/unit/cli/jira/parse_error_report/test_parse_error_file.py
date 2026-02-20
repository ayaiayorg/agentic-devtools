"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge

from agdt_ai_helpers.cli.jira.parse_error_report import (
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
