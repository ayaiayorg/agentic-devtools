"""
Tests for prompt template loader.
"""

import pytest

from agentic_devtools.prompts import loader


class TestLoadAndRenderPrompt:
    """Tests for load_and_render_prompt function."""

    def test_load_and_render_full_workflow(self, temp_prompts_dir, temp_output_dir):
        """Test full load and render workflow."""
        template_content = "Hello {{name}}, working on {{task}}"
        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template_content, encoding="utf-8")

        context = {"name": "Alice", "task": "PROJECT-1234"}
        result = loader.load_and_render_prompt("test", "initiate", context)

        assert result == "Hello Alice, working on PROJECT-1234"

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

    def test_warns_on_missing_template_variables(self, temp_prompts_dir, temp_output_dir, capsys):
        """Missing template variables produce a warning on stderr."""
        template_content = "Hello {{name}}, working on {{task}}"
        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(template_content, encoding="utf-8")

        # Provide only one of the two declared variables
        loader.load_and_render_prompt("test", "initiate", {"name": "Alice"})

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "task" in captured.err
        assert "test/initiate" in captured.err

    def test_no_warning_when_all_variables_provided(self, temp_prompts_dir, temp_output_dir, capsys):
        """No warning is printed when all template variables are provided."""
        template_content = "Hello {{name}}, working on {{task}}"
        workflow_dir = temp_prompts_dir / "test"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(template_content, encoding="utf-8")

        loader.load_and_render_prompt("test", "initiate", {"name": "Alice", "task": "T1"})

        captured = capsys.readouterr()
        assert "WARNING" not in captured.err
