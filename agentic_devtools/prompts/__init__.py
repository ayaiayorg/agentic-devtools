"""
Prompt template system for workflow commands.

This module provides functionality for loading, validating, and rendering
prompt templates used by workflow initiation commands.

Key features:
- Overrideable prompts: default templates can be overridden by user templates
- Variable validation: ensures override templates include all required variables
- Multi-step workflows: supports different prompts for different workflow steps
- Generated prompt output: saves rendered prompts to temp folder for reference
"""

from .loader import (
    TemplateValidationError,
    get_prompts_dir,
    get_required_variables,
    get_temp_output_dir,
    load_and_render_prompt,
    load_prompt_template,
    log_prompt_with_save_notice,
    save_generated_prompt,
    substitute_variables,
    validate_template_variables,
)

__all__ = [
    "get_prompts_dir",
    "get_temp_output_dir",
    "load_prompt_template",
    "validate_template_variables",
    "substitute_variables",
    "get_required_variables",
    "save_generated_prompt",
    "load_and_render_prompt",
    "log_prompt_with_save_notice",
    "TemplateValidationError",
]
