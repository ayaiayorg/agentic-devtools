"""Tests for get_issue_value."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.github.state_helpers import get_issue_value


@pytest.fixture
def temp_state(tmp_path):
    """Create a temporary state directory."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        state.clear_state()
        yield tmp_path


class TestGetIssueValue:
    """Tests for get_issue_value."""

    def test_returns_none_when_not_set(self, temp_state):
        """Returns None when key is not in state."""
        result = get_issue_value("title")
        assert result is None

    def test_returns_value_when_set(self, temp_state):
        """Returns value stored under issue.<key>."""
        state.set_value("issue.title", "My issue")
        result = get_issue_value("title")
        assert result == "My issue"

    def test_namespace_prefix(self, temp_state):
        """Value is stored/retrieved under 'issue.' prefix."""
        state.set_value("issue.description", "Some description")
        result = get_issue_value("description")
        assert result == "Some description"

    def test_different_keys_independent(self, temp_state):
        """Different keys within namespace are independent."""
        state.set_value("issue.title", "Title value")
        state.set_value("issue.description", "Desc value")
        assert get_issue_value("title") == "Title value"
        assert get_issue_value("description") == "Desc value"

    def test_required_false_returns_none_when_missing(self, temp_state):
        """required=False returns None when key is missing (default behavior)."""
        result = get_issue_value("nonexistent", required=False)
        assert result is None

    def test_required_true_raises_when_missing(self, temp_state):
        """required=True raises an error when key is missing."""
        with pytest.raises(Exception):
            get_issue_value("nonexistent", required=True)

    def test_required_true_returns_value_when_set(self, temp_state):
        """required=True returns value when key is present."""
        state.set_value("issue.title", "My title")
        result = get_issue_value("title", required=True)
        assert result == "My title"
