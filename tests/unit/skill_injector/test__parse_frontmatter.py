"""Tests for agentic_devtools.skill_injector._parse_frontmatter."""

from agentic_devtools.skill_injector import _parse_frontmatter


class TestParseFrontmatter:
    """Tests for the _parse_frontmatter helper."""

    def test_extracts_yaml_frontmatter(self):
        """Extracts a simple YAML front-matter block and includes fallback description from body."""
        content = "---\ndescription: Hello World\n---\n# Body"
        result = _parse_frontmatter(content)
        assert result == {"description": "Hello World", "_agdt_fallback_description": "Body"}

    def test_returns_fallback_dict_when_no_frontmatter(self):
        """Returns fallback description dict when content has no front-matter."""
        result = _parse_frontmatter("# Just a heading\nSome text")
        assert result == {"_agdt_fallback_description": "Just a heading"}

    def test_returns_fallback_dict_when_no_closing_delimiter(self):
        """Returns fallback description dict when closing --- is missing."""
        result = _parse_frontmatter("---\ndescription: broken\n# No close")
        assert result == {"_agdt_fallback_description": "description: broken"}

    def test_returns_empty_dict_on_malformed_yaml(self):
        """Returns empty dict when YAML is malformed."""
        result = _parse_frontmatter("---\n: :\n  - [\n---\n")
        assert result == {}

    def test_returns_empty_dict_when_yaml_is_not_dict(self):
        """Returns empty dict when YAML parses to a non-dict (e.g. a list)."""
        result = _parse_frontmatter("---\n- item1\n- item2\n---\n")
        assert result == {}

    def test_extracts_multiline_frontmatter(self):
        """Extracts multiple keys from front-matter."""
        content = "---\ndescription: Test\nagent: my-agent\n---\n"
        result = _parse_frontmatter(content)
        assert result["description"] == "Test"
        assert result["agent"] == "my-agent"

    def test_returns_fallback_dict_when_frontmatter_is_empty(self):
        """Returns fallback description dict when front-matter block is empty."""
        result = _parse_frontmatter("---\n---\n# Body")
        assert result == {"_agdt_fallback_description": "Body"}

    def test_handles_quoted_values(self):
        """Handles YAML values with quotes."""
        content = '---\ndescription: "Quoted value"\n---\n'
        result = _parse_frontmatter(content)
        assert result["description"] == "Quoted value"

    def test_handles_single_quoted_values(self):
        """Handles YAML values with single quotes."""
        content = "---\ndescription: 'Single quoted'\n---\n"
        result = _parse_frontmatter(content)
        assert result["description"] == "Single quoted"

    def test_handles_crlf_line_endings(self):
        """Extracts front-matter correctly when content uses CRLF line endings."""
        content = "---\r\ndescription: Hello World\r\n---\r\n# Body"
        result = _parse_frontmatter(content)
        assert result == {"description": "Hello World", "_agdt_fallback_description": "Body"}
