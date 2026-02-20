"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agdt_ai_helpers.prompts import loader


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
