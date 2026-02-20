"""
Tests for parse_error_report module - Jira error report parsing.

Note: Test data contains German text with unicode escapes (e.g., k\\u00f6nnen).
"""
# cspell:ignore nnen nge

from agdt_ai_helpers.cli.jira.parse_error_report import (
    _parse_error_file,
)


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
