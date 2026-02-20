"""Tests for the review_commands module and helper functions."""


from agdt_ai_helpers.cli.azure_devops.review_helpers import (
    convert_to_prompt_filename,
)


class TestConvertToPromptFilename:
    """Tests for convert_to_prompt_filename function."""

    def test_basic_path(self):
        """Test conversion of a basic file path."""
        result = convert_to_prompt_filename("/path/to/file.ts")
        assert result.startswith("file-")
        assert result.endswith(".md")
        assert len(result) == 24  # "file-" + 16 chars + ".md"

    def test_empty_path(self):
        """Test conversion of empty path."""
        result = convert_to_prompt_filename("")
        assert result == "file-metadata-missing.md"

    def test_same_path_same_hash(self):
        """Test same path produces same hash."""
        result1 = convert_to_prompt_filename("/path/to/file.ts")
        result2 = convert_to_prompt_filename("/path/to/file.ts")
        assert result1 == result2

    def test_different_paths_different_hashes(self):
        """Test different paths produce different hashes."""
        result1 = convert_to_prompt_filename("/path/to/file1.ts")
        result2 = convert_to_prompt_filename("/path/to/file2.ts")
        assert result1 != result2
