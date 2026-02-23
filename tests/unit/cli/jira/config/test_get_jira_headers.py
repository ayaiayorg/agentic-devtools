"""
Tests for Jira configuration and authentication.
"""

from unittest.mock import patch

from agdt_ai_helpers.cli import jira


class TestJiraAuth:
    """Tests for Jira authentication."""

    def test_get_jira_headers(self):
        """Test get_jira_headers returns proper headers."""
        with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
            headers = jira.get_jira_headers()
            assert "Authorization" in headers
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
