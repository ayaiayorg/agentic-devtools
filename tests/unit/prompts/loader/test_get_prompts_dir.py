"""
Tests for prompt template loader.
"""

from pathlib import Path

from agdt_ai_helpers.prompts import loader


class TestGetPromptsDir:
    """Tests for get_prompts_dir function."""

    def test_returns_path_object(self):
        """Test that get_prompts_dir returns a Path object."""
        result = loader.get_prompts_dir()
        assert isinstance(result, Path)

    def test_path_ends_with_prompts(self):
        """Test that path ends with 'prompts' directory."""
        result = loader.get_prompts_dir()
        assert result.name == "prompts"
