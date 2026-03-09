"""Tests for _matches_pattern internal function."""

from agentic_devtools.cli.azure_devops.review_config import _matches_pattern


class TestMatchesPattern:
    """Tests for _matches_pattern."""

    def test_exact_match(self):
        """Exact filename match."""
        assert _matches_pattern("src/file.ts", "src/file.ts") is True

    def test_wildcard_match(self):
        """Wildcard in pattern matches any filename."""
        assert _matches_pattern("src/file.ts", "src/*.ts") is True

    def test_no_match(self):
        """Non-matching path returns False."""
        assert _matches_pattern("other/file.ts", "src/*.ts") is False

    def test_recursive_glob(self):
        """** matches across directories."""
        assert _matches_pattern("src/deep/nested/file.ts", "src/**") is True

    def test_backslash_normalized(self):
        """Backslashes are normalized to forward slashes."""
        assert _matches_pattern("src\\file.ts", "src/*.ts") is True

    def test_suffix_match(self):
        """Matches when pattern matches a suffix of the path."""
        assert _matches_pattern("a/b/c/file.test.ts", "*.test.ts") is True

    def test_suffix_match_via_loop(self):
        """Matches via suffix loop when full-path fnmatch fails."""
        # Full path "src/app/file.ts" does NOT match "app/*.ts"
        # But suffix "app/file.ts" does match "app/*.ts"
        assert _matches_pattern("src/app/file.ts", "app/*.ts") is True

    def test_no_suffix_match(self):
        """Returns False when no suffix matches."""
        assert _matches_pattern("a/b/c/file.ts", "*.test.ts") is False
