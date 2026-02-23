"""Tests for set_issue_value."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.github.state_helpers import set_issue_value


@pytest.fixture
def temp_state(tmp_path):
    """Create a temporary state directory."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        state.clear_state()
        yield tmp_path


class TestSetIssueValue:
    """Tests for set_issue_value."""

    def test_sets_value_with_namespace_prefix(self, temp_state):
        """Value is stored under 'issue.<key>' in state."""
        set_issue_value("title", "My issue")
        result = state.get_value("issue.title")
        assert result == "My issue"

    def test_overwrites_existing_value(self, temp_state):
        """Calling set_issue_value again overwrites previous value."""
        set_issue_value("title", "First")
        set_issue_value("title", "Second")
        result = state.get_value("issue.title")
        assert result == "Second"

    def test_stores_different_types(self, temp_state):
        """Can store string, int, and bool values."""
        set_issue_value("count", 42)
        set_issue_value("flag", True)
        assert state.get_value("issue.count") == 42
        assert state.get_value("issue.flag") is True
