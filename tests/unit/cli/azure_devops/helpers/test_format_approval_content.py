"""Tests for format_approval_content helper."""
from agentic_devtools import state
from agentic_devtools.cli import azure_devops
from unittest.mock import MagicMock, patch
import pytest

class TestFormatApprovalContent:
    """Tests for format_approval_content helper."""

    def test_adds_sentinel_to_content(self):
        """Test that approval sentinel is added to content."""
        content = "LGTM! All tests pass."
        result = azure_devops.format_approval_content(content)
        assert result.startswith(azure_devops.APPROVAL_SENTINEL)
        assert result.strip().endswith(azure_devops.APPROVAL_SENTINEL)
        assert "LGTM! All tests pass." in result

    def test_already_formatted_unchanged(self):
        """Test already formatted content is unchanged."""
        formatted = f"{azure_devops.APPROVAL_SENTINEL}\n\nContent\n\n{azure_devops.APPROVAL_SENTINEL}"
        result = azure_devops.format_approval_content(formatted)
        assert result == formatted

    def test_empty_string(self):
        """Test empty string gets wrapped."""
        result = azure_devops.format_approval_content("")
        assert azure_devops.APPROVAL_SENTINEL in result
