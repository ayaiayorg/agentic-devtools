"""Tests for the review_commands module and helper functions."""

from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    normalize_repo_path,
)


class TestNormalizeRepoPath:
    """Tests for normalize_repo_path function."""

    def test_basic_path(self):
        """Test normalization of basic path."""
        result = normalize_repo_path("src/app/file.ts")
        assert result == "/src/app/file.ts"

    def test_path_with_leading_slash(self):
        """Test path with leading slash."""
        result = normalize_repo_path("/src/app/file.ts")
        assert result == "/src/app/file.ts"

    def test_path_with_backslashes(self):
        """Test path with Windows backslashes."""
        result = normalize_repo_path("src\\app\\file.ts")
        assert result == "/src/app/file.ts"

    def test_empty_path(self):
        """Test empty path returns None."""
        result = normalize_repo_path("")
        assert result is None

    def test_none_path(self):
        """Test None path returns None."""
        result = normalize_repo_path(None)
        assert result is None

    def test_whitespace_only(self):
        """Test whitespace-only path returns None."""
        result = normalize_repo_path("   ")
        assert result is None


class TestNormalizePathForComparison:
    """Tests for _normalize_path_for_comparison function."""

    def test_basic_path(self):
        """Test normalization of basic path."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("src/app/file.ts")
        assert result == "src/app/file.ts"

    def test_path_with_leading_slash(self):
        """Test path with leading slash has it stripped."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("/src/app/file.ts")
        assert result == "src/app/file.ts"

    def test_path_with_backslashes(self):
        """Test path with Windows backslashes converted."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("src\\app\\file.ts")
        assert result == "src/app/file.ts"

    def test_lowercase_normalization(self):
        """Test path is lowercased."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("SRC/App/File.ts")
        assert result == "src/app/file.ts"

    def test_empty_path(self):
        """Test empty path returns empty."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("")
        assert result == ""

    def test_mixed_normalization(self):
        """Test combination of normalizations."""
        from agdt_ai_helpers.cli.azure_devops.review_commands import _normalize_path_for_comparison

        result = _normalize_path_for_comparison("/SRC\\App/File.ts")
        assert result == "src/app/file.ts"
