"""
Tests for Jira configuration and authentication.
"""

from unittest.mock import patch

import pytest

from agdt_ai_helpers.cli import jira


class TestJiraAuth:
    """Tests for Jira authentication."""

    def test_auth_header_bearer_default(self):
        """Test bearer token auth (default)."""
        with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
            header = jira.get_jira_auth_header()
            assert header == "Bearer test-token"

    def test_auth_header_bearer_explicit(self):
        """Test bearer token auth with explicit scheme."""
        with patch.dict(
            "os.environ",
            {"JIRA_COPILOT_PAT": "test-token", "JIRA_AUTH_SCHEME": "bearer"},
        ):
            header = jira.get_jira_auth_header()
            assert header == "Bearer test-token"

    def test_auth_header_token_scheme(self):
        """Test token scheme (alias for bearer)."""
        with patch.dict(
            "os.environ",
            {"JIRA_COPILOT_PAT": "test-token", "JIRA_AUTH_SCHEME": "token"},
        ):
            header = jira.get_jira_auth_header()
            assert header == "Bearer test-token"

    def test_auth_header_basic_with_email(self):
        """Test basic auth with email."""
        with patch.dict(
            "os.environ",
            {
                "JIRA_COPILOT_PAT": "test-token",
                "JIRA_AUTH_SCHEME": "basic",
                "JIRA_EMAIL": "test@example.com",
            },
        ):
            header = jira.get_jira_auth_header()
            assert header.startswith("Basic ")

    def test_auth_header_basic_with_username(self):
        """Test basic auth with username."""
        with patch.dict(
            "os.environ",
            {
                "JIRA_COPILOT_PAT": "test-token",
                "JIRA_AUTH_SCHEME": "basic",
                "JIRA_USERNAME": "testuser",
            },
        ):
            header = jira.get_jira_auth_header()
            assert header.startswith("Basic ")

    def test_auth_header_missing_pat_raises(self):
        """Test missing PAT raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                jira.get_jira_auth_header()
            assert "JIRA_COPILOT_PAT" in str(exc_info.value)

    def test_auth_header_basic_missing_identity_raises(self):
        """Test basic auth without identity raises error."""
        with patch.dict(
            "os.environ",
            {"JIRA_COPILOT_PAT": "test-token", "JIRA_AUTH_SCHEME": "basic"},
            clear=True,
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                jira.get_jira_auth_header()
            assert "JIRA_EMAIL" in str(exc_info.value)

    def test_auth_header_unsupported_scheme_raises(self):
        """Test unsupported auth scheme raises error."""
        with patch.dict(
            "os.environ",
            {"JIRA_COPILOT_PAT": "test-token", "JIRA_AUTH_SCHEME": "oauth"},
        ):
            with pytest.raises(ValueError) as exc_info:
                jira.get_jira_auth_header()
            assert "oauth" in str(exc_info.value)
