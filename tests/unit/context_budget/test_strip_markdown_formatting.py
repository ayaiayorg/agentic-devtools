"""Tests for strip_markdown_formatting()."""

from agentic_devtools.context_budget import strip_markdown_formatting


class TestStripMarkdownFormatting:
    """Verify markdown formatting is stripped while preserving code content."""

    def test_empty_string(self):
        assert strip_markdown_formatting("") == ""

    def test_plain_text_unchanged(self):
        text = "Hello world, this is plain text."
        assert strip_markdown_formatting(text) == text

    def test_strips_headings(self):
        text = "# Heading 1\n## Heading 2\n### Heading 3"
        result = strip_markdown_formatting(text)
        assert "# " not in result
        assert "## " not in result
        assert "### " not in result
        assert "Heading 1" in result
        assert "Heading 2" in result
        assert "Heading 3" in result

    def test_strips_bold(self):
        assert "important" in strip_markdown_formatting("**important**")
        assert "**" not in strip_markdown_formatting("**important**")

    def test_preserves_bold_underscore(self):
        """Underscore-based bold (__text__) is intentionally preserved to avoid
        corrupting identifiers like __init__ and foo_bar."""
        result = strip_markdown_formatting("__important__")
        assert "__important__" in result

    def test_strips_italic(self):
        assert "emphasis" in strip_markdown_formatting("*emphasis*")

    def test_preserves_italic_underscore(self):
        """Underscore-based italic (_text_) is intentionally preserved to avoid
        corrupting identifiers like foo_bar."""
        result = strip_markdown_formatting("_emphasis_")
        assert "_emphasis_" in result

    def test_strips_links_preserves_text(self):
        result = strip_markdown_formatting("[click here](https://example.com)")
        assert "click here" in result
        assert "https://example.com" not in result
        assert "[" not in result

    def test_strips_horizontal_rules(self):
        result = strip_markdown_formatting("above\n---\nbelow")
        assert "---" not in result
        assert "above" in result
        assert "below" in result

    def test_preserves_fenced_code_blocks(self):
        text = "text\n```python\ndef foo():\n    return 42\n```\nmore"
        result = strip_markdown_formatting(text)
        assert "def foo():" in result
        assert "return 42" in result

    def test_preserves_tilde_fenced_code_blocks(self):
        text = "text\n~~~\ncode here\n~~~\nmore"
        result = strip_markdown_formatting(text)
        assert "code here" in result

    def test_preserves_indented_code_blocks(self):
        text = "text\n    indented code\n    more code\nnormal"
        result = strip_markdown_formatting(text)
        assert "indented code" in result
        assert "more code" in result

    def test_preserves_indented_code_at_end_of_file(self):
        text = "text\n    indented code at end"
        result = strip_markdown_formatting(text)
        assert "indented code at end" in result

    def test_preserves_inline_code_spans(self):
        text = "Use the `foo()` function"
        result = strip_markdown_formatting(text)
        assert "`foo()`" in result

    def test_preserves_snake_case_names(self):
        """Underscores in identifiers like foo_bar_baz must not be stripped."""
        text = "The variable foo_bar_baz is important."
        result = strip_markdown_formatting(text)
        assert "foo_bar_baz" in result

    def test_preserves_dunder_names(self):
        """Dunder names like __init__ must not be stripped."""
        text = "See the __init__ method and __main__ module."
        result = strip_markdown_formatting(text)
        assert "__init__" in result
        assert "__main__" in result

    def test_preserves_mid_word_underscores(self):
        """Underscores within compound identifiers must not be treated as emphasis."""
        text = "Use my_var_name and some_other_thing in code."
        result = strip_markdown_formatting(text)
        assert "my_var_name" in result
        assert "some_other_thing" in result
