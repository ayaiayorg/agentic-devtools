"""
Tests for Jira state namespace helpers.
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers import state
from agdt_ai_helpers.cli import jira


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


class TestJiraStateHelpers:
    """Tests for Jira state namespace helpers."""

    def test_set_jira_value_creates_nested_structure(self, temp_state_dir, clear_state_before):
        """Test setting a jira value creates nested structure."""
        jira.set_jira_value("summary", "My Summary")
        loaded = state.load_state()
        assert loaded == {"jira": {"summary": "My Summary"}}

    def test_set_jira_value_preserves_other_keys(self, temp_state_dir, clear_state_before):
        """Test setting jira value preserves other namespace keys."""
        state.set_value("other_key", "other_value")
        jira.set_jira_value("summary", "My Summary")
        loaded = state.load_state()
        assert loaded["other_key"] == "other_value"
        assert loaded["jira"]["summary"] == "My Summary"

