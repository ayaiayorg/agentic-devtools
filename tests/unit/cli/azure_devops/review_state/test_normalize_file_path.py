"""Tests for normalize_file_path function."""

from agentic_devtools.cli.azure_devops.review_state import normalize_file_path


class TestNormalizeFilePath:
    """Tests for normalize_file_path function."""

    def test_adds_leading_slash_when_missing(self):
        """Test that a leading slash is added when missing."""
        assert normalize_file_path("src/app.py") == "/src/app.py"

    def test_preserves_existing_leading_slash(self):
        """Test that an existing leading slash is not duplicated."""
        assert normalize_file_path("/src/app.py") == "/src/app.py"

    def test_deep_path(self):
        """Test normalization of a deep path without leading slash."""
        assert normalize_file_path("a/b/c/d.py") == "/a/b/c/d.py"

    def test_file_in_root(self):
        """Test normalization of a root-level file."""
        assert normalize_file_path("app.py") == "/app.py"

    def test_already_normalized_deep_path(self):
        """Test that already-normalized deep path is unchanged."""
        assert normalize_file_path("/a/b/c/d.py") == "/a/b/c/d.py"

    def test_windows_style_path_preserves_backslashes(self):
        """Test that Windows-style paths preserve backslashes while adding leading slash."""
        result = normalize_file_path("src\\app.py")
        assert result == "/src\\app.py"
