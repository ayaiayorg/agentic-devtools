"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agdt_ai_helpers.prompts import loader


class TestLoadAndRenderPrompt:
    """Tests for load_and_render_prompt function."""

    def test_load_and_render_full_workflow(self, temp_prompts_dir, temp_output_dir):
        """Test full load and render workflow."""
        template_content = "Hello {{name}}, working on {{task}}"
        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template_content, encoding="utf-8")

        context = {"name": "Alice", "task": "DFLY-1234"}
        result = loader.load_and_render_prompt("test", "initiate", context)

        assert result == "Hello Alice, working on DFLY-1234"

    def test_load_and_render_with_override(self, temp_prompts_dir, temp_output_dir):
        """Test load and render with override template."""
        default_content = "Default {{name}}"
        override_content = "Custom: {{name}}"

        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()

        default_file = workflow_dir / "default-initiate-prompt.md"
        default_file.write_text(default_content, encoding="utf-8")

        # Override filename has no prefix (no 'default-')
        override_file = workflow_dir / "initiate-prompt.md"
        override_file.write_text(override_content, encoding="utf-8")

        context = {"name": "Bob"}
        result = loader.load_and_render_prompt("test", "initiate", context)

        assert result == "Custom: Bob"

    def test_load_and_render_validates_override(self, temp_prompts_dir, temp_output_dir):
        """Test that override is validated against default."""
        default_content = "{{name}}"
        override_content = "{{name}} {{extra}}"

        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()

        default_file = workflow_dir / "default-initiate-prompt.md"
        default_file.write_text(default_content, encoding="utf-8")

        # Override filename has no prefix (no 'default-')
        override_file = workflow_dir / "initiate-prompt.md"
        override_file.write_text(override_content, encoding="utf-8")

        with pytest.raises(loader.TemplateValidationError):
            loader.load_and_render_prompt("test", "initiate", {"name": "Test"})
