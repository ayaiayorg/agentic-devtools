"""
Prompt template loading and variable substitution.

This module handles:
- Loading prompt templates (with override support)
- Variable extraction and validation
- Variable substitution in templates
- Saving generated prompts to temp folder
- Console output with save notice
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from jinja2 import BaseLoader, Environment, TemplateSyntaxError, Undefined


class TemplateValidationError(Exception):
    """Raised when template validation fails (e.g., missing required variables)."""

    def __init__(self, message: str, missing_variables: List[str]):
        super().__init__(message)
        self.missing_variables = missing_variables


def get_prompts_dir() -> Path:
    """
    Get the directory containing prompt templates.

    Returns:
        Path to the prompts directory (agentic_devtools/prompts/)
    """
    return Path(__file__).parent


def get_temp_output_dir() -> Path:
    """
    Get the temp directory for generated prompts.

    Delegates to ``get_state_dir()`` so that the directory respects the
    ``AGENTIC_DEVTOOLS_STATE_DIR`` environment variable.  This ensures that
    when a command is executed inside a worktree via
    ``_run_auto_execute_command``, prompt files are written to the worktree's
    ``scripts/temp/`` rather than a path relative to the installed package.

    Returns:
        Path to scripts/temp/ directory
    """
    from ..state import get_state_dir

    temp_dir = get_state_dir()
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def get_template_filename(workflow_name: str, step_name: str = "initiate", is_default: bool = True) -> str:
    """
    Build the template filename based on naming convention.

    Templates are organized in subfolders per workflow:
    - Default: <workflow>/<prefix>default-<step>-prompt.md
    - Override: <workflow>/<step>-prompt.md

    Args:
        workflow_name: Name of the workflow (e.g., "pull-request-review")
        step_name: Name of the step (e.g., "initiate", "review-file")
        is_default: If True, return the default template filename

    Returns:
        Template filename (just the filename, not the path)
    """
    prefix = "default-" if is_default else ""
    return f"{prefix}{step_name}-prompt.md"


def get_template_path(workflow_name: str, step_name: str = "initiate", is_default: bool = True) -> Path:
    """
    Build the full path to a template file.

    Templates are organized in subfolders per workflow:
    - prompts/<workflow>/default-<step>-prompt.md (default)
    - prompts/<workflow>/<step>-prompt.md (override)

    Args:
        workflow_name: Name of the workflow (e.g., "pull-request-review")
        step_name: Name of the step (e.g., "initiate", "review-file")
        is_default: If True, return path to the default template

    Returns:
        Full path to the template file
    """
    prompts_dir = get_prompts_dir()
    filename = get_template_filename(workflow_name, step_name, is_default)
    return prompts_dir / workflow_name / filename


def get_required_variables(template_content: str) -> Set[str]:
    """
    Extract variable names from template content.

    Variables use {{variable}} syntax (double curly braces).

    Args:
        template_content: Template content to parse

    Returns:
        Set of variable names found in the template
    """
    # Match {{variableName}} pattern
    pattern = r"\{\{(\w+)\}\}"
    matches = re.findall(pattern, template_content)
    return set(matches)


def validate_template_variables(default_content: str, override_content: str) -> None:
    """
    Validate that override template doesn't introduce new variables.

    Override templates can use a subset of the default template's variables,
    but they cannot introduce new variables that are not in the default.
    This ensures that all required state keys are documented in the default.

    Args:
        default_content: Content of the default template
        override_content: Content of the override template

    Raises:
        TemplateValidationError: If override introduces new variables
    """
    default_vars = get_required_variables(default_content)
    override_vars = get_required_variables(override_content)

    extra_vars = override_vars - default_vars
    if extra_vars:
        raise TemplateValidationError(
            f"Override template uses variables not in default: {extra_vars}",
            missing_variables=list(extra_vars),
        )


# Custom Jinja2 undefined class that renders as empty string and is falsy


class SilentUndefined(Undefined):
    """Custom undefined class that renders as empty string and is falsy."""

    def _fail_with_undefined_error(self, *args, **kwargs):
        return ""

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:
        return ""

    def __bool__(self) -> bool:
        return False

    def __iter__(self):
        return iter([])

    def __len__(self) -> int:
        return 0


# Create a Jinja2 environment configured for our templates
# - Keep {{ }} for variables (Jinja2 default)
# - Keep {% %} for control structures (Jinja2 default)
# - SilentUndefined makes missing variables render as empty strings
_jinja_env = Environment(
    loader=BaseLoader(),
    autoescape=False,  # nosec B701 - templates generate markdown, not HTML; autoescape is intentionally disabled
    keep_trailing_newline=True,
    undefined=SilentUndefined,
)


def substitute_variables(template: str, variables: Dict[str, Any]) -> str:
    """
    Replace {{variable}} placeholders with actual values using Jinja2.

    Supports full Jinja2 templating:
    - {{ variable }} - replaced with the value
    - {% if variable %}...{% endif %} - conditional blocks
    - {% for item in list %}...{% endfor %} - loops
    - Filters: {{ variable | default('fallback') }}
    - And more...

    Args:
        template: Template content with Jinja2 syntax
        variables: Dictionary mapping variable names to values

    Returns:
        Template with variables substituted
    """
    try:
        jinja_template = _jinja_env.from_string(template)
        return jinja_template.render(**variables)
    except TemplateSyntaxError:
        # If Jinja2 can't parse it, fall back to simple regex substitution
        # This handles edge cases where templates might have literal {{ }} that aren't variables
        result = template
        for var_name, value in variables.items():
            str_value = str(value) if value is not None else ""
            pattern = r"\{\{\s*" + re.escape(var_name) + r"\s*\}\}"
            result = re.sub(pattern, str_value.replace("\\", "\\\\"), result)
        return result


def load_prompt_template(
    workflow_name: str,
    step_name: str = "initiate",
    validate_override: bool = True,
) -> str:
    """
    Load a prompt template, preferring override if it exists.

    Args:
        workflow_name: Name of the workflow (e.g., "pull-request-review")
        step_name: Name of the step (e.g., "initiate", "review-file")
        validate_override: If True, validate that override has all required variables

    Returns:
        Template content

    Raises:
        FileNotFoundError: If no template (default or override) exists
        TemplateValidationError: If override introduces new variables not in default
    """
    # Build full paths using the new subfolder structure
    default_path = get_template_path(workflow_name, step_name, is_default=True)
    override_path = get_template_path(workflow_name, step_name, is_default=False)

    # Check for override first
    if override_path.exists():
        override_content = override_path.read_text(encoding="utf-8")

        if validate_override and default_path.exists():
            default_content = default_path.read_text(encoding="utf-8")
            # This will raise TemplateValidationError if override has extra variables
            validate_template_variables(default_content, override_content)

        return override_content

    # Fall back to default
    if default_path.exists():
        return default_path.read_text(encoding="utf-8")

    # No template found
    raise FileNotFoundError(
        f"No prompt template found for workflow '{workflow_name}', step '{step_name}'.\nExpected file: {default_path}"
    )


def save_generated_prompt(workflow_name: str, step_name: str, content: str) -> Path:
    """
    Save a generated prompt to the temp folder.

    Args:
        workflow_name: Name of the workflow
        step_name: Name of the step
        content: Generated prompt content

    Returns:
        Path to the saved file
    """
    temp_dir = get_temp_output_dir()

    # Ensure directory exists
    temp_dir.mkdir(parents=True, exist_ok=True)

    filename = f"temp-{workflow_name}-{step_name}-prompt.md"
    output_path = temp_dir / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def log_prompt_with_save_notice(
    workflow_name: str,
    step_name: str,
    content: str,
    saved_path: Optional[Path] = None,
) -> None:
    """
    Log the prompt to console with header/footer and save notice.

    Output format:
    ================================================================================
    WORKFLOW: pull-request-review
    STEP: initiate
    ================================================================================

    [prompt content]

    ================================================================================
    The exact prompt logged above is also saved to:
      scripts/temp/temp-pull-request-review-initiate-prompt.md
    ================================================================================

    Args:
        workflow_name: Name of the workflow
        step_name: Name of the step
        content: Generated prompt content
        saved_path: Path where the prompt was saved (if None, computes default)
    """
    if saved_path is None:
        saved_path = get_temp_output_dir() / f"temp-{workflow_name}-{step_name}-prompt.md"

    separator = "=" * 80

    # Use sys.stdout.buffer for safe Unicode output on Windows
    def safe_print(text: str) -> None:
        """Print text safely, handling Unicode encoding issues on Windows."""
        try:
            print(text)
        except UnicodeEncodeError:  # pragma: no cover
            # Fall back to writing to buffer with UTF-8 encoding
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()

    safe_print(separator)
    safe_print(f"WORKFLOW: {workflow_name}")
    safe_print(f"STEP: {step_name}")
    safe_print(separator)
    safe_print("")
    safe_print(content)
    safe_print("")
    safe_print(separator)
    safe_print("The exact prompt logged above is also saved to:")
    safe_print(f"  {saved_path}")
    safe_print(separator)
    sys.stdout.flush()


def load_and_render_prompt(
    workflow_name: str,
    step_name: str,
    variables: Dict[str, Any],
    save_to_temp: bool = True,
    log_output: bool = True,
) -> str:
    """
    Load template, substitute variables, optionally save and log.

    This is a convenience function that combines the common workflow of:
    1. Loading the template (override or default)
    2. Substituting variables
    3. Saving to temp folder
    4. Logging with save notice

    Args:
        workflow_name: Name of the workflow
        step_name: Name of the step
        variables: Dictionary of variables to substitute
        save_to_temp: If True, save generated prompt to temp folder
        log_output: If True, log prompt to console with save notice

    Returns:
        The generated prompt content

    Raises:
        FileNotFoundError: If no template exists
        TemplateValidationError: If override is missing required variables
    """
    # Load template
    template = load_prompt_template(workflow_name, step_name)

    # Substitute variables
    content = substitute_variables(template, variables)

    # Save to temp
    saved_path = None
    if save_to_temp:
        saved_path = save_generated_prompt(workflow_name, step_name, content)

    # Log output
    if log_output:
        log_prompt_with_save_notice(workflow_name, step_name, content, saved_path)

    return content
