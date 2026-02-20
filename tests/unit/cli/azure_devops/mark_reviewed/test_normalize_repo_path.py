"""
Tests for mark_reviewed module - Azure DevOps PR file review marking.
"""

from agentic_devtools.cli.azure_devops.mark_reviewed import (
    normalize_repo_path,
)


class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_normalize_simple_path(self):
        """Test normalizing a simple path."""
        assert normalize_repo_path("path/to/file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_leading_slash(self):
        """Test path that already has leading slash."""
        assert normalize_repo_path("/path/to/file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_backslashes(self):
        """Test path with Windows-style backslashes."""
        assert normalize_repo_path("path\\to\\file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_trailing_slash(self):
        """Test path with trailing slash."""
        assert normalize_repo_path("path/to/folder/") == "/path/to/folder"

    def test_normalize_path_with_multiple_leading_slashes(self):
        """Test path with multiple leading slashes."""
        assert normalize_repo_path("///path/to/file.ts") == "/path/to/file.ts"

    def test_normalize_path_with_whitespace(self):
        """Test path with leading/trailing whitespace."""
        assert normalize_repo_path("  path/to/file.ts  ") == "/path/to/file.ts"

    def test_normalize_path_mixed_slashes(self):
        """Test path with mixed slashes."""
        assert normalize_repo_path("path\\to/file\\name.ts") == "/path/to/file/name.ts"

    def test_normalize_empty_path(self):
        """Test empty path returns None."""
        assert normalize_repo_path("") is None

    def test_normalize_whitespace_only(self):
        """Test whitespace-only path returns None."""
        assert normalize_repo_path("   ") is None

    def test_normalize_none_path(self):
        """Test None path returns None."""
        assert normalize_repo_path(None) is None

    def test_normalize_single_file(self):
        """Test single filename without directory."""
        assert normalize_repo_path("file.ts") == "/file.ts"

    def test_normalize_deep_path(self):
        """Test deeply nested path."""
        path = "a/b/c/d/e/f/file.ts"
        assert normalize_repo_path(path) == "/a/b/c/d/e/f/file.ts"

    def test_normalize_path_with_dots(self):
        """Test path with dots."""
        assert normalize_repo_path("src/.github/copilot-instructions.md") == "/src/.github/copilot-instructions.md"

    def test_normalize_path_with_special_characters(self):
        """Test path with special characters (allowed in filenames)."""
        assert normalize_repo_path("path/to/file-name_v2.ts") == "/path/to/file-name_v2.ts"


class TestNormalizeRepoPathEdgeCases:
    """Additional edge case tests for normalize_repo_path."""

    def test_normalize_path_only_slashes(self):
        """Test path that is only slashes (cleans to empty)."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import normalize_repo_path

        # "///" after stripping becomes "" which should return None
        assert normalize_repo_path("///") is None

    def test_normalize_path_only_backslashes(self):
        """Test path that is only backslashes."""
        from agentic_devtools.cli.azure_devops.mark_reviewed import normalize_repo_path

        assert normalize_repo_path("\\\\\\") is None
