"""Tests for require_content helper."""
import pytest

from agentic_devtools import state
from agentic_devtools.cli import azure_devops


class TestRequireContent:
    """Tests for require_content helper."""

    def test_returns_content_when_set(self, temp_state_dir, clear_state_before):
        """Test returns content when available."""
        state.set_value("content", "Test content")
        result = azure_devops.require_content()
        assert result == "Test content"

    def test_exits_when_content_missing(self, temp_state_dir, clear_state_before):
        """Test exits when content not set."""
        with pytest.raises(SystemExit) as exc_info:
            azure_devops.require_content()
        assert exc_info.value.code == 1
