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


class TestJiraAuth:
    """Tests for Jira authentication."""

    def test_get_jira_headers(self):
        """Test get_jira_headers returns proper headers."""
        with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
            headers = jira.get_jira_headers()
            assert "Authorization" in headers
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
