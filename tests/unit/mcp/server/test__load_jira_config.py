"""Tests for agentic_devtools.mcp.server._load_jira_config."""

import base64
import os
from unittest.mock import patch

from agentic_devtools.mcp.server import _load_jira_config
from agentic_devtools.tools.jira import JiraConfig


class TestLoadJiraConfig:
    """Tests for the _load_jira_config helper."""

    def test_returns_config_when_all_vars_set(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert isinstance(result, JiraConfig)
        assert result.base_url == "https://jira.example.com"
        assert result.ssl_verify is True

    def test_returns_none_when_base_url_missing(self):
        env = {"JIRA_API_TOKEN": "tok123"}
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is None

    def test_returns_none_when_token_missing(self):
        env = {"JIRA_BASE_URL": "https://jira.example.com"}
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is None

    def test_returns_none_when_both_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _load_jira_config()

        assert result is None

    def test_basic_auth_when_email_set(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
            "JIRA_USER_EMAIL": "user@example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        expected = base64.b64encode(b"user@example.com:tok123").decode()
        assert result.headers == {"Authorization": f"Basic {expected}"}

    def test_bearer_auth_when_email_not_set(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.headers == {"Authorization": "Bearer tok123"}

    def test_ssl_verify_false_with_zero(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
            "JIRA_SSL_VERIFY": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.ssl_verify is False

    def test_ssl_verify_false_with_false_string(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
            "JIRA_SSL_VERIFY": "false",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.ssl_verify is False

    def test_ssl_verify_false_case_insensitive(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
            "JIRA_SSL_VERIFY": "FALSE",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.ssl_verify is False

    def test_ssl_verify_path(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
            "JIRA_SSL_VERIFY": "/path/to/cert.pem",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.ssl_verify == "/path/to/cert.pem"

    def test_ssl_verify_default_true(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "tok123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.ssl_verify is True

    def test_token_falls_back_to_jira_copilot_pat(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_COPILOT_PAT": "copilot-tok",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.headers == {"Authorization": "Bearer copilot-tok"}

    def test_token_prefers_jira_api_token_over_fallback(self):
        env = {
            "JIRA_BASE_URL": "https://jira.example.com",
            "JIRA_API_TOKEN": "primary-tok",
            "JIRA_COPILOT_PAT": "copilot-tok",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_jira_config()

        assert result is not None
        assert result.headers == {"Authorization": "Bearer primary-tok"}
