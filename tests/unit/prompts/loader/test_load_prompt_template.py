"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agdt_ai_helpers.prompts import loader


class TestLoadPromptTemplate:
    """Tests for load_prompt_template function."""

    def test_load_default_template(self, temp_prompts_dir):
        """Test loading a default template."""
        template_content = "# Workflow\n\n{{variable}}"
        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template_content, encoding="utf-8")

        result = loader.load_prompt_template("test", "initiate")
        assert result == template_content

    def test_load_override_template_when_exists(self, temp_prompts_dir):
        """Test that override template is preferred when it exists."""
        default_content = "Default {{var}}"
        override_content = "Override {{var}}"

        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()

        default_file = workflow_dir / "default-initiate-prompt.md"
        default_file.write_text(default_content, encoding="utf-8")

        # Override filename has no prefix (no 'default-')
        override_file = workflow_dir / "initiate-prompt.md"
        override_file.write_text(override_content, encoding="utf-8")

        result = loader.load_prompt_template("test", "initiate")
        assert result == override_content

    def test_load_template_file_not_found(self, temp_prompts_dir):
        """Test that FileNotFoundError is raised for missing template."""
        with pytest.raises(FileNotFoundError):
            loader.load_prompt_template("nonexistent", "initiate")
