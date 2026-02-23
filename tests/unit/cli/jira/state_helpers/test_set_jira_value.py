"""
Tests for Jira state namespace helpers.
"""

from agdt_ai_helpers import state
from agdt_ai_helpers.cli import jira


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
