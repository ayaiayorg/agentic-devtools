"""
Tests for Jira configuration and authentication.
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


class TestJiraConfiguration:
    """Tests for Jira configuration functions."""

    def test_default_jira_base_url(self, temp_state_dir, clear_state_before):
        """Test default Jira base URL."""
        with patch.dict("os.environ", {}, clear=True):
            url = jira.get_jira_base_url()
            assert url == jira.DEFAULT_JIRA_BASE_URL

    def test_jira_base_url_from_env(self, temp_state_dir, clear_state_before):
        """Test Jira base URL from environment."""
        with patch.dict("os.environ", {"JIRA_BASE_URL": "https://custom.jira.com"}):
            url = jira.get_jira_base_url()
            assert url == "https://custom.jira.com"

    def test_jira_base_url_from_state(self, temp_state_dir, clear_state_before):
        """Test Jira base URL from state takes precedence."""
        state.set_value("jira_base_url", "https://state.jira.com")
        with patch.dict("os.environ", {"JIRA_BASE_URL": "https://env.jira.com"}):
            url = jira.get_jira_base_url()
            assert url == "https://state.jira.com"
