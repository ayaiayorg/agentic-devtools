"""Tests for agentic_devtools.state.set_value."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


class TestSetValue:
    """Tests for set_value function."""

    def test_set_and_get_value(self, temp_state_dir):
        """Test setting and getting a simple value."""
        state.set_value("test_key", "test_value")
        assert state.get_value("test_key") == "test_value"

    def test_set_integer_value(self, temp_state_dir):
        """Test setting an integer value."""
        state.set_value("count", 42)
        assert state.get_value("count") == 42

    def test_set_float_value(self, temp_state_dir):
        """Test setting a float value."""
        state.set_value("ratio", 3.14)
        assert state.get_value("ratio") == 3.14

    def test_set_boolean_value(self, temp_state_dir):
        """Test setting a boolean value."""
        state.set_value("flag", True)
        assert state.get_value("flag") is True

    def test_set_list_value(self, temp_state_dir):
        """Test setting a list value."""
        items = ["a", "b", "c"]
        state.set_value("items", items)
        assert state.get_value("items") == items

    def test_set_dict_value(self, temp_state_dir):
        """Test setting a dictionary value."""
        config = {"key": "value", "nested": {"inner": 1}}
        state.set_value("config", config)
        assert state.get_value("config") == config


class TestSetValueSpecialCharacters:
    """Tests for handling special characters in set_value."""

    def test_parentheses_in_content(self, temp_state_dir):
        """Test that parentheses are preserved."""
        content = "This (has) parentheses"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_brackets_in_content(self, temp_state_dir):
        """Test that brackets are preserved."""
        content = "Array [0] and [1]"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_braces_in_content(self, temp_state_dir):
        """Test that braces are preserved."""
        content = "Object {key: value}"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_mixed_special_characters(self, temp_state_dir):
        """Test mixed special characters."""
        content = "func(arg) { return array[0]; }"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_unicode_characters(self, temp_state_dir):
        """Test Unicode characters are preserved."""
        content = "Größe Übung Äpfel 你好 🎉"
        state.set_value("content", content)
        assert state.get_value("content") == content


class TestSetValueMultilineContent:
    """Tests for handling multiline content in set_value."""

    def test_simple_multiline(self, temp_state_dir):
        """Test simple multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_multiline_with_empty_lines(self, temp_state_dir):
        """Test multiline with empty lines."""
        content = "Line 1\n\nLine 3 after empty"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_multiline_with_special_chars(self, temp_state_dir):
        """Test multiline with special characters."""
        content = """Thanks for the feedback!

I've fixed the issue:
- Updated function(arg)
- Fixed array[0] access
- Changed {config}"""
        state.set_value("content", content)
        assert state.get_value("content") == content
