"""
Tests for prompt template loader.
"""

from unittest.mock import patch

from agdt_ai_helpers.prompts import loader


class TestSaveGeneratedPrompt:
    """Tests for save_generated_prompt function."""

    def test_save_generated_prompt(self, temp_output_dir):
        """Test saving a generated prompt."""
        prompt_content = "# Generated Prompt\n\nThis is content."
        filepath = loader.save_generated_prompt("test", "initiate", prompt_content)

        assert filepath.exists()
        assert filepath.read_text(encoding="utf-8") == prompt_content
        assert filepath.name == "temp-test-initiate-prompt.md"

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates output directory if needed."""
        output_dir = tmp_path / "new_dir" / "nested"
        with patch.object(loader, "get_temp_output_dir", return_value=output_dir):
            filepath = loader.save_generated_prompt("test", "step", "content")
            assert filepath.parent.exists()
