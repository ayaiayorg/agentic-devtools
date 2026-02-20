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

    def test_get_jira_value_returns_value(self, temp_state_dir, clear_state_before):
        """Test getting a value from jira namespace."""
        state.set_value("jira.summary", "Test Summary")
        assert jira.get_jira_value("summary") == "Test Summary"

    def test_get_jira_value_returns_none_for_missing(self, temp_state_dir, clear_state_before):
        """Test getting a missing value returns None."""
        assert jira.get_jira_value("nonexistent") is None

    def test_get_jira_value_required_raises_error(self, temp_state_dir, clear_state_before):
        """Test getting a required missing value raises error."""
        with pytest.raises(KeyError):
            jira.get_jira_value("nonexistent", required=True)

    def test_namespace_constant_is_used(self):
        """Test that JIRA_STATE_NAMESPACE constant is defined and used."""
        assert jira.JIRA_STATE_NAMESPACE == "jira"

