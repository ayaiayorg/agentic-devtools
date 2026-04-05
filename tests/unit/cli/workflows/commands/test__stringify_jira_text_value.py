"""Tests for _stringify_jira_text_value helper function."""

from agentic_devtools.cli.workflows.commands import _stringify_jira_text_value


class TestStringifyJiraTextValue:
    """Tests for ADF-aware text value normalisation."""

    def test_none_returns_default(self):
        """None value should return the provided default."""
        assert _stringify_jira_text_value(None, "fallback") == "fallback"

    def test_empty_string_returns_default(self):
        """Empty string should return the provided default."""
        assert _stringify_jira_text_value("", "fallback") == "fallback"

    def test_plain_string_returned_as_is(self):
        """A plain string should be returned unchanged."""
        assert _stringify_jira_text_value("hello world", "fallback") == "hello world"

    def test_adf_dict_converted_to_text(self):
        """An ADF dict should be converted to plain text via _convert_adf_to_text."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello from ADF"}],
                }
            ],
        }
        result = _stringify_jira_text_value(adf, "fallback")
        assert "Hello from ADF" in result
        assert result != "fallback"

    def test_empty_adf_dict_returns_default(self):
        """An ADF dict that yields no text should return the default."""
        assert _stringify_jira_text_value({}, "fallback") == "fallback"

    def test_non_string_non_dict_uses_str(self):
        """Other types should be stringified via str()."""
        assert _stringify_jira_text_value(42, "fallback") == "42"

    def test_non_string_non_dict_empty_str_returns_default(self):
        """Types whose str() is falsy should return the default."""
        # bool False → str "False" which is truthy, so this returns "False"
        assert _stringify_jira_text_value(False, "fallback") == "False"

    def test_list_uses_str(self):
        """A list value should be stringified via str()."""
        result = _stringify_jira_text_value(["a", "b"], "fallback")
        assert result == "['a', 'b']"

    def test_adf_with_multiple_paragraphs(self):
        """ADF with multiple paragraphs should be converted to multiline text."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Line 1"}],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Line 2"}],
                },
            ],
        }
        result = _stringify_jira_text_value(adf, "fallback")
        assert "Line 1" in result
        assert "Line 2" in result
