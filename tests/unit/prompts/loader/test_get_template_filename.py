"""
Tests for prompt template loader.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from agdt_ai_helpers.prompts import loader


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
