"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agdt_ai_helpers.prompts import loader


class TestLogPromptWithSaveNotice:
    """Tests for log_prompt_with_save_notice function."""

    def test_log_outputs_prompt_content(self, capsys, temp_output_dir):
        """Test that log outputs the prompt content."""
        prompt_content = "# Prompt\n\nContent here"
        loader.log_prompt_with_save_notice("test", "step", prompt_content)

        captured = capsys.readouterr()
        assert "# Prompt" in captured.out
        assert "Content here" in captured.out

    def test_log_includes_save_path(self, capsys, temp_output_dir):
        """Test that log includes where prompt was saved."""
        loader.log_prompt_with_save_notice("test", "step", "content")

        captured = capsys.readouterr()
        assert "temp-test-step-prompt.md" in captured.out
