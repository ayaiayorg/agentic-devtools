"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agdt_ai_helpers.prompts import loader


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with patch.object(loader, "get_prompts_dir", return_value=prompts_dir):
        yield prompts_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir):
        yield output_dir


class TestGetTemplateFilename:
    """Tests for get_template_filename function."""

    def test_default_template_filename(self):
        """Test generating default template filename."""
        filename = loader.get_template_filename("pull-request-review", "initiate")
        assert filename == "default-initiate-prompt.md"

    def test_override_template_filename(self):
        """Test generating override template filename."""
        filename = loader.get_template_filename("pull-request-review", "initiate", is_default=False)
        assert filename == "initiate-prompt.md"

    def test_different_steps(self):
        """Test generating filenames for different steps."""
        assert loader.get_template_filename("workflow", "plan") == "default-plan-prompt.md"
        assert loader.get_template_filename("workflow", "execute") == "default-execute-prompt.md"


class TestGetTemplatePath:
    """Tests for get_template_path function."""

    def test_default_template_path(self, temp_prompts_dir):
        """Test generating default template path."""
        path = loader.get_template_path("pull-request-review", "initiate")
        assert path.parent.name == "pull-request-review"
        assert path.name == "default-initiate-prompt.md"

    def test_override_template_path(self, temp_prompts_dir):
        """Test generating override template path."""
        path = loader.get_template_path("pull-request-review", "initiate", is_default=False)
        assert path.parent.name == "pull-request-review"
        assert path.name == "initiate-prompt.md"

    def test_step_template_path(self, temp_prompts_dir):
        """Test generating step template path."""
        path = loader.get_template_path("work-on-jira-issue", "planning")
        assert path.parent.name == "work-on-jira-issue"
        assert path.name == "default-planning-prompt.md"


class TestGetRequiredVariables:
    """Tests for get_required_variables function."""

    def test_extract_single_variable(self):
        """Test extracting a single variable."""
        template = "Hello {{name}}"
        variables = loader.get_required_variables(template)
        assert variables == {"name"}

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables."""
        template = "Issue {{jira_issue_key}} in project {{project_name}}"
        variables = loader.get_required_variables(template)
        assert variables == {"jira_issue_key", "project_name"}

    def test_no_variables(self):
        """Test template with no variables."""
        template = "This is plain text"
        variables = loader.get_required_variables(template)
        assert variables == set()

    def test_duplicate_variables(self):
        """Test that duplicate variables are deduplicated."""
        template = "{{name}} and {{name}} again"
        variables = loader.get_required_variables(template)
        assert variables == {"name"}

    def test_complex_variable_names(self):
        """Test variables with underscores."""
        template = "{{pull_request_id}} and {{jira_issue_key}}"
        variables = loader.get_required_variables(template)
        assert variables == {"pull_request_id", "jira_issue_key"}


class TestValidateTemplateVariables:
    """Tests for validate_template_variables function."""

    def test_validation_passes_with_all_required(self):
        """Test validation passes when all required variables are provided."""
        default_template = "Hello {{name}}, welcome to {{project}}"
        override_template = "Hi {{name}}, enjoy {{project}}"
        # Should not raise
        loader.validate_template_variables(default_template, override_template)

    def test_validation_passes_with_subset(self):
        """Test validation passes when override uses subset of variables."""
        default_template = "Hello {{name}}, welcome to {{project}}"
        override_template = "Hi {{name}}"
        # Should not raise - override can use fewer variables
        loader.validate_template_variables(default_template, override_template)

    def test_validation_fails_with_extra_variables(self):
        """Test validation fails when override introduces new variables."""
        default_template = "Hello {{name}}"
        override_template = "Hello {{name}}, from {{location}}"
        with pytest.raises(loader.TemplateValidationError) as exc_info:
            loader.validate_template_variables(default_template, override_template)
        assert "location" in str(exc_info.value)

    def test_validation_error_lists_missing_variables(self):
        """Test that validation error includes missing variable names."""
        default_template = "Hello {{name}}"
        override_template = "{{greeting}} {{name}} from {{city}}"
        with pytest.raises(loader.TemplateValidationError) as exc_info:
            loader.validate_template_variables(default_template, override_template)
        error_msg = str(exc_info.value)
        assert "greeting" in error_msg or "city" in error_msg


class TestSubstituteVariables:
    """Tests for substitute_variables function."""

    def test_substitute_single_variable(self):
        """Test substituting a single variable."""
        template = "Hello {{name}}"
        result = loader.substitute_variables(template, {"name": "World"})
        assert result == "Hello World"

    def test_substitute_multiple_variables(self):
        """Test substituting multiple variables."""
        template = "Issue {{key}} in {{project}}"
        result = loader.substitute_variables(template, {"key": "DFLY-1234", "project": "Dragonfly"})
        assert result == "Issue DFLY-1234 in Dragonfly"

    def test_substitute_duplicate_variable(self):
        """Test substituting a variable that appears multiple times."""
        template = "{{name}} says hello, {{name}} waves goodbye"
        result = loader.substitute_variables(template, {"name": "Alice"})
        assert result == "Alice says hello, Alice waves goodbye"

    def test_substitute_missing_variable_becomes_empty(self):
        """Test that missing variables render as empty strings."""
        template = "Hello {{name}}"
        result = loader.substitute_variables(template, {})
        # With Jinja2's SilentUndefined, missing variables render as empty strings
        assert result == "Hello "

    def test_substitute_preserves_extra_context(self):
        """Test that extra context keys don't affect substitution."""
        template = "Hello {{name}}"
        result = loader.substitute_variables(template, {"name": "World", "unused": "value"})
        assert result == "Hello World"

    def test_conditional_with_truthy_variable(self):
        """Test that {% if %} blocks are included when variable is truthy."""
        template = "Start{% if jira_key %} - Issue: {{jira_key}}{% endif %} End"
        result = loader.substitute_variables(template, {"jira_key": "DFLY-1234"})
        assert result == "Start - Issue: DFLY-1234 End"

    def test_conditional_with_falsy_empty_string(self):
        """Test that {% if %} blocks are removed when variable is empty string."""
        template = "Start{% if jira_key %} - Issue: {{jira_key}}{% endif %} End"
        result = loader.substitute_variables(template, {"jira_key": ""})
        assert result == "Start End"

    def test_conditional_with_missing_variable(self):
        """Test that {% if %} blocks are removed when variable is missing."""
        template = "Start{% if jira_key %} - Issue: {{jira_key}}{% endif %} End"
        result = loader.substitute_variables(template, {})
        assert result == "Start End"

    def test_conditional_multiline_content(self):
        """Test that {% if %} blocks work with multiline content."""
        template = """Header
{% if show_details %}
- Detail 1
- Detail 2: {{value}}
{% endif %}
Footer"""
        result = loader.substitute_variables(template, {"show_details": True, "value": "test"})
        assert "Detail 1" in result
        assert "Detail 2: test" in result

    def test_conditional_multiline_removed_when_falsy(self):
        """Test that multiline {% if %} blocks are removed when variable is falsy."""
        template = """Header
{% if show_details %}
- Detail 1
- Detail 2: {{value}}
{% endif %}
Footer"""
        result = loader.substitute_variables(template, {"show_details": False, "value": "test"})
        assert "Detail" not in result
        assert "Header" in result
        assert "Footer" in result


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


class TestTemplateValidationError:
    """Tests for TemplateValidationError class."""

    def test_error_stores_missing_variables(self):
        """Test that error stores missing variables."""
        error = loader.TemplateValidationError("Test error", ["var1", "var2"])
        assert set(error.missing_variables) == {"var1", "var2"}

    def test_error_message_includes_variables(self):
        """Test that error message includes variable names."""
        error = loader.TemplateValidationError("Override has extra variables: var1, var2", ["var1", "var2"])
        message = str(error)
        assert "var1" in message or "var2" in message

    def test_error_message_readable(self):
        """Test that error message is human readable."""
        error = loader.TemplateValidationError(
            "Override template uses variables not in default: {'missing_var'}",
            ["missing_var"],
        )
        message = str(error)
        assert "override" in message.lower() or "variable" in message.lower()


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
