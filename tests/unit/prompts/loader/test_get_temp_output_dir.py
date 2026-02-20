"""
Tests for prompt template loader.
"""

from pathlib import Path

from agdt_ai_helpers.prompts import loader


class TestGetTempOutputDir:
    """Tests for get_temp_output_dir function."""

    def test_returns_path_object(self):
        """Test that get_temp_output_dir returns a Path object."""
        result = loader.get_temp_output_dir()
        assert isinstance(result, Path)

    def test_path_is_in_temp_directory(self):
        """Test that path is in temp directory."""
        result = loader.get_temp_output_dir()
        # Should be scripts/temp/
        assert "temp" in str(result)
