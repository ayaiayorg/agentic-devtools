"""
Tests for prompt template loader.
"""

import pytest

from agdt_ai_helpers.prompts import loader


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
