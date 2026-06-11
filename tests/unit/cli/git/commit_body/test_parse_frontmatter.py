"""Tests for parse_frontmatter function."""

from agentic_devtools.cli.git.commit_body import parse_frontmatter


class TestParseFrontmatter:
    """Tests for parse_frontmatter."""

    def test_no_frontmatter(self):
        """Test content without frontmatter returns empty dict and full content."""
        content = "## Summary\n\n- item 1\n- item 2"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_valid_frontmatter(self):
        """Test valid YAML frontmatter is parsed and stripped from body."""
        content = "---\nchecklist: [1, 2, 3]\nstatus: approved\n---\n## Body\n\nContent"
        fm, body = parse_frontmatter(content)
        assert fm == {"checklist": [1, 2, 3], "status": "approved"}
        assert body == "## Body\n\nContent"

    def test_malformed_yaml(self, capsys):
        """Test malformed YAML returns empty dict and full content with warning."""
        content = "---\n: invalid: [yaml: {\n---\nBody text"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content
        captured = capsys.readouterr()
        assert "Malformed YAML" in captured.err

    def test_none_result_treated_as_empty_dict(self):
        """Test YAML that parses to None returns empty dict, body after closing."""
        content = "---\n\n---\nBody after empty frontmatter"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == "Body after empty frontmatter"

    def test_non_dict_result_treated_as_malformed(self, capsys):
        """Test YAML that parses to non-dict (e.g., list) is malformed."""
        content = "---\n- item1\n- item2\n---\nBody text"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content
        captured = capsys.readouterr()
        assert "not a mapping" in captured.err

    def test_no_closing_delimiter(self):
        """Test missing closing --- treats entire content as body."""
        content = "---\nkey: value\nno closing delimiter"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_frontmatter_with_nested_dict(self):
        """Test nested dict values in frontmatter."""
        content = "---\nmeta:\n  key1: val1\n  key2: val2\n---\nBody"
        fm, body = parse_frontmatter(content)
        assert fm == {"meta": {"key1": "val1", "key2": "val2"}}
        assert body == "Body"

    def test_frontmatter_with_list_of_integers(self):
        """Test list of integers in frontmatter."""
        content = "---\nitems: [1, 2, 3, 4]\n---\nBody content"
        fm, body = parse_frontmatter(content)
        assert fm == {"items": [1, 2, 3, 4]}
        assert body == "Body content"

    def test_bom_before_opening_delimiter(self):
        """Test BOM before opening --- (BOM should be stripped before calling)."""
        # BOM stripping happens in read_commit_body, but if somehow passed here:
        content = "\ufeff---\nkey: value\n---\nBody"
        # The BOM prefix means it won't match startswith("---")
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content
