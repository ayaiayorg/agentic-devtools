"""Tests for agentic_devtools.cli.git.diff.normalize_ref_name."""

from agentic_devtools.cli.git.diff import normalize_ref_name


class TestNormalizeRefName:
    """Tests for normalize_ref_name function."""

    def test_strips_refs_heads_prefix(self):
        """Should strip refs/heads/ prefix from ref names."""
        result = normalize_ref_name("refs/heads/main")
        assert result == "main"

    def test_strips_refs_heads_prefix_with_slashes(self):
        """Should handle ref names with slashes."""
        result = normalize_ref_name("refs/heads/feature/my-branch")
        assert result == "feature/my-branch"

    def test_returns_unchanged_if_no_prefix(self):
        """Should return ref unchanged if no prefix."""
        result = normalize_ref_name("main")
        assert result == "main"

    def test_returns_none_for_none(self):
        """Should return None for None input."""
        result = normalize_ref_name(None)
        assert result is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        result = normalize_ref_name("")
        assert result is None
