"""
Tests for Atlassian Document Format (ADF) conversion.
"""

from agdt_ai_helpers.cli import jira


class TestProcessAdfChildren:
    """Tests for _process_adf_children function."""

    def test_process_empty_node(self):
        """Test empty node returns empty string."""
        assert jira._process_adf_children({}) == ""

    def test_process_node_without_content(self):
        """Test node without content key returns empty string."""
        assert jira._process_adf_children({"type": "doc"}) == ""

    def test_process_node_with_content(self):
        """Test node with content processes children."""
        node = {"content": [{"text": "Hello"}, {"text": " World"}]}
        result = jira._process_adf_children(node)
        assert result == "Hello World"

    def test_process_node_with_empty_content(self):
        """Test node with empty content list."""
        node = {"content": []}
        assert jira._process_adf_children(node) == ""

    def test_process_node_filters_empty_parts(self):
        """Test empty parts are filtered from result."""
        node = {"content": [{"text": "Hello"}, {}, {"text": "World"}]}
        result = jira._process_adf_children(node)
        assert "Hello" in result
        assert "World" in result
