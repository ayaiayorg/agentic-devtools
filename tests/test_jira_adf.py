"""
Tests for Atlassian Document Format (ADF) conversion.
"""

from dfly_ai_helpers.cli import jira


class TestConvertAdfToText:
    """Tests for _convert_adf_to_text function."""

    def test_convert_none(self):
        """Test None input returns empty string."""
        assert jira._convert_adf_to_text(None) == ""

    def test_convert_string(self):
        """Test string input returns same string."""
        assert jira._convert_adf_to_text("Hello") == "Hello"

    def test_convert_text_node(self):
        """Test text node conversion."""
        node = {"text": "Hello World"}
        assert jira._convert_adf_to_text(node) == "Hello World"

    def test_convert_paragraph(self):
        """Test paragraph conversion."""
        node = {"type": "paragraph", "content": [{"text": "Hello"}]}
        result = jira._convert_adf_to_text(node)
        assert "Hello" in result
        assert result.endswith("\n")

    def test_convert_paragraph_empty(self):
        """Test empty paragraph conversion."""
        node = {"type": "paragraph", "content": []}
        assert jira._convert_adf_to_text(node) == ""

    def test_convert_heading(self):
        """Test heading conversion."""
        node = {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"text": "My Heading"}],
        }
        result = jira._convert_adf_to_text(node)
        assert "## My Heading" in result

    def test_convert_heading_default_level(self):
        """Test heading without level defaults to 1."""
        node = {"type": "heading", "content": [{"text": "Heading"}]}
        result = jira._convert_adf_to_text(node)
        assert result.startswith("# ")

    def test_convert_heading_empty(self):
        """Test empty heading conversion."""
        node = {"type": "heading", "attrs": {"level": 1}, "content": []}
        assert jira._convert_adf_to_text(node) == ""

    def test_convert_bullet_list(self):
        """Test bullet list conversion."""
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"text": "Item 1"}]}],
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"text": "Item 2"}]}],
                },
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "• Item 1" in result
        assert "• Item 2" in result

    def test_convert_bullet_list_empty(self):
        """Test empty bullet list conversion."""
        node = {"type": "bulletList", "content": []}
        assert jira._convert_adf_to_text(node) == ""

    def test_convert_ordered_list(self):
        """Test ordered list conversion."""
        node = {
            "type": "orderedList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"text": "First"}]}],
                },
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"text": "Second"}]}],
                },
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "1. First" in result
        assert "2. Second" in result

    def test_convert_ordered_list_empty(self):
        """Test empty ordered list conversion."""
        node = {"type": "orderedList", "content": []}
        assert jira._convert_adf_to_text(node) == ""

    def test_convert_code_block(self):
        """Test code block conversion."""
        node = {"type": "codeBlock", "content": [{"text": "print('hello')"}]}
        result = jira._convert_adf_to_text(node)
        assert "```" in result
        assert "print('hello')" in result

    def test_convert_code_block_empty(self):
        """Test empty code block conversion."""
        node = {"type": "codeBlock", "content": []}
        assert jira._convert_adf_to_text(node) == ""

    def test_convert_blockquote(self):
        """Test blockquote conversion."""
        node = {
            "type": "blockquote",
            "content": [{"type": "paragraph", "content": [{"text": "Quote text"}]}],
        }
        result = jira._convert_adf_to_text(node)
        assert "> " in result
        assert "Quote text" in result

    def test_convert_blockquote_empty(self):
        """Test empty blockquote conversion."""
        node = {"type": "blockquote", "content": []}
        assert jira._convert_adf_to_text(node) == ""

    def test_convert_hard_break(self):
        """Test hard break conversion."""
        node = {"type": "hardBreak"}
        assert jira._convert_adf_to_text(node) == "\n"

    def test_convert_list_item(self):
        """Test list item processes children."""
        node = {
            "type": "listItem",
            "content": [{"type": "paragraph", "content": [{"text": "Item text"}]}],
        }
        result = jira._convert_adf_to_text(node)
        assert "Item text" in result

    def test_convert_nested_content(self):
        """Test nested content conversion."""
        node = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"text": "Hello"}]},
                {"type": "paragraph", "content": [{"text": "World"}]},
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "Hello" in result
        assert "World" in result

    def test_convert_list_input(self):
        """Test list of nodes conversion."""
        nodes = [{"text": "Hello "}, {"text": "World"}]
        result = jira._convert_adf_to_text(nodes)
        assert result == "Hello World"

    def test_convert_empty_list_input(self):
        """Test empty list returns empty string."""
        assert jira._convert_adf_to_text([]) == ""

    def test_convert_unknown_type(self):
        """Test unknown node type processes children."""
        node = {"type": "customType", "content": [{"text": "Content"}]}
        result = jira._convert_adf_to_text(node)
        assert result == "Content"

    def test_convert_dict_without_type_or_text(self):
        """Test dict without type or text processes content."""
        node = {"content": [{"text": "Hello"}]}
        result = jira._convert_adf_to_text(node)
        assert result == "Hello"

    def test_convert_nested_indentation(self):
        """Test nested list indentation."""
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"text": "Item"}]}],
                }
            ],
        }
        result = jira._convert_adf_to_text(node, indent_level=1)
        assert "  •" in result  # Should have indentation


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


class TestConvertAdfEdgeCases:
    """Edge case tests for ADF conversion."""

    def test_convert_multiline_blockquote(self):
        """Test blockquote with multiple lines."""
        node = {
            "type": "blockquote",
            "content": [
                {"type": "paragraph", "content": [{"text": "Line 1"}]},
                {"type": "paragraph", "content": [{"text": "Line 2"}]},
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "> Line 1" in result or "> " in result

    def test_convert_deeply_nested_structure(self):
        """Test deeply nested ADF structure."""
        node = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"text": "Nested item"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "Nested item" in result

    def test_convert_text_with_integer_value(self):
        """Test text node with integer value."""
        node = {"text": 123}
        result = jira._convert_adf_to_text(node)
        assert result == "123"

    def test_convert_list_item_skips_empty_text(self):
        """Test list items with empty text are handled."""
        node = {
            "type": "bulletList",
            "content": [
                {"type": "listItem", "content": []},
                {
                    "type": "listItem",
                    "content": [{"type": "paragraph", "content": [{"text": "Valid"}]}],
                },
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "Valid" in result

    def test_convert_heading_level_3(self):
        """Test heading level 3."""
        node = {
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"text": "H3 Heading"}],
        }
        result = jira._convert_adf_to_text(node)
        assert "### H3 Heading" in result

    def test_convert_mixed_content_in_paragraph(self):
        """Test paragraph with mixed text nodes."""
        node = {
            "type": "paragraph",
            "content": [
                {"text": "Hello "},
                {"text": "World", "marks": [{"type": "strong"}]},
                {"text": "!"},
            ],
        }
        result = jira._convert_adf_to_text(node)
        assert "Hello World!" in result

    def test_convert_numeric_input(self):
        """Test numeric input returns empty string (fallback case)."""
        assert jira._convert_adf_to_text(12345) == ""

    def test_convert_boolean_input(self):
        """Test boolean input returns empty string (fallback case)."""
        assert jira._convert_adf_to_text(True) == ""

    def test_convert_float_input(self):
        """Test float input returns empty string (fallback case)."""
        assert jira._convert_adf_to_text(3.14) == ""
