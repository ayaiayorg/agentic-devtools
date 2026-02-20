"""Tests for the review_commands module and helper functions."""


from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    get_root_folder,
)


class TestGetRootFolder:
    """Tests for get_root_folder function."""

    def test_basic_path(self):
        """Test extraction from basic path."""
        result = get_root_folder("src/app/file.ts")
        assert result == "src"

    def test_file_only(self):
        """Test file with no folder returns 'root'."""
        result = get_root_folder("file.ts")
        assert result == "root"

    def test_empty_path(self):
        """Test empty path returns 'root'."""
        result = get_root_folder("")
        assert result == "root"

    def test_backslash_path(self):
        """Test path with backslashes."""
        result = get_root_folder("src\\app\\file.ts")
        assert result == "src"

    def test_none_path(self):
        """Test None path returns 'root'."""
        result = get_root_folder(None)
        assert result == "root"
