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
            # Should contain base64 of 'test@example.com:test-token'

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

    def test_get_jira_headers(self):
        """Test get_jira_headers returns proper headers."""
        with patch.dict("os.environ", {"JIRA_COPILOT_PAT": "test-token"}):
            headers = jira.get_jira_headers()
            assert "Authorization" in headers
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"
