"""Tests for agentic_devtools.context.nodes.retrieve_context_node."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentic_devtools.context.nodes import _build_jira_config, _utc_now, retrieve_context_node


class TestUtcNow:
    """Tests for the _utc_now helper."""

    def test_returns_string(self):
        result = _utc_now()
        assert isinstance(result, str)

    def test_returns_valid_iso_format(self):
        from datetime import datetime

        result = _utc_now()
        parsed = datetime.fromisoformat(result)
        assert parsed.tzinfo is not None


class TestBuildJiraConfig:
    """Tests for _build_jira_config helper."""

    def test_bearer_auth_with_token(self, monkeypatch):
        """Uses Bearer auth when only token is set and no auth scheme override."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "my-token")
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)

        config = _build_jira_config()
        assert config.base_url == "https://jira.example.com"
        assert config.headers["Authorization"] == "Bearer my-token"
        assert config.ssl_verify is True

    def test_basic_auth_with_email_and_token(self, monkeypatch):
        """Uses Basic auth when both email and token are set."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_USER_EMAIL", "user@example.com")
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)

        config = _build_jira_config()
        assert "Basic" in config.headers["Authorization"]

    def test_auth_scheme_basic_forces_basic(self, monkeypatch):
        """JIRA_AUTH_SCHEME=basic forces Basic auth when email+token are set."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_USER_EMAIL", "user@example.com")
        monkeypatch.setenv("JIRA_AUTH_SCHEME", "basic")
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)

        config = _build_jira_config()
        assert "Basic" in config.headers["Authorization"]

    def test_auth_scheme_basic_no_email_no_auth(self, monkeypatch):
        """JIRA_AUTH_SCHEME=basic without email produces no Authorization header."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_AUTH_SCHEME", "basic")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)

        config = _build_jira_config()
        assert "Authorization" not in config.headers

    def test_empty_env_vars(self, monkeypatch):
        """Empty env vars produce a config with empty base_url and no auth."""
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)

        config = _build_jira_config()
        assert config.base_url == ""
        assert "Authorization" not in config.headers

    def test_ssl_verify_disabled(self, monkeypatch):
        """JIRA_SSL_VERIFY=0 disables SSL verification."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_SSL_VERIFY", "0")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)

        config = _build_jira_config()
        assert config.ssl_verify is False

    def test_ssl_verify_ca_bundle(self, monkeypatch):
        """Non-zero JIRA_SSL_VERIFY is treated as CA bundle path."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_SSL_VERIFY", "/path/to/ca.pem")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)

        config = _build_jira_config()
        assert config.ssl_verify == "/path/to/ca.pem"

    def test_copilot_pat_fallback(self, monkeypatch):
        """Falls back to JIRA_COPILOT_PAT when JIRA_API_TOKEN is missing."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.setenv("JIRA_COPILOT_PAT", "copilot-token")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)

        config = _build_jira_config()
        assert config.headers["Authorization"] == "Bearer copilot-token"

    def test_ssl_verify_false_string(self, monkeypatch):
        """JIRA_SSL_VERIFY=false disables SSL verification."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_SSL_VERIFY", "false")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)

        config = _build_jira_config()
        assert config.ssl_verify is False


class TestRetrieveContextNode:
    """Tests for the retrieve_context_node async function."""

    @pytest.mark.asyncio
    async def test_missing_issue_key(self):
        """Returns error dict when issue_key is missing from state."""
        result = await retrieve_context_node({})
        assert result["agent_context"] == {}
        assert result["error"] == "issue_key is required for context retrieval"
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "context_retrieval_failed"

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.nodes.IssueContextRetriever")
    async def test_happy_path(self, mock_retriever_cls, monkeypatch, tmp_path):
        """Successful retrieval returns agent_context, events, and clears error."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)
        monkeypatch.chdir(tmp_path)

        mock_ctx = MagicMock()
        mock_ctx.to_dict.return_value = {"issue_key": "T-1"}
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_ctx)
        mock_retriever_cls.return_value = mock_retriever

        state = {"issue_key": "T-1", "affected_paths": ["src/main.py"]}
        result = await retrieve_context_node(state)

        assert result["agent_context"] == {"issue_key": "T-1"}
        assert len(result["events"]) == 1
        assert result["events"][0]["event"] == "context_retrieval_completed"
        assert result["error"] is None
        mock_retriever.retrieve.assert_awaited_once_with("T-1", ["src/main.py"])

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.nodes.IssueContextRetriever")
    async def test_constructs_jira_config_from_env(self, mock_retriever_cls, monkeypatch, tmp_path):
        """Node constructs JiraConfig from environment variables."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.test.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.chdir(tmp_path)

        mock_ctx = MagicMock()
        mock_ctx.to_dict.return_value = {}
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_ctx)
        mock_retriever_cls.return_value = mock_retriever

        await retrieve_context_node({"issue_key": "X-1"})

        # Verify the JiraConfig was constructed
        call_kwargs = mock_retriever_cls.call_args
        config = call_kwargs[1]["jira_config"]
        assert config.base_url == "https://jira.test.com"
        assert "Bearer test-token" in config.headers.get("Authorization", "")

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.nodes.IssueContextRetriever")
    async def test_missing_env_vars_still_runs(self, mock_retriever_cls, monkeypatch, tmp_path):
        """Node handles missing env vars — JiraConfig has empty base_url."""
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.chdir(tmp_path)

        mock_ctx = MagicMock()
        mock_ctx.to_dict.return_value = {"errors": ["base_url is required"]}
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_ctx)
        mock_retriever_cls.return_value = mock_retriever

        result = await retrieve_context_node({"issue_key": "T-1"})

        assert "agent_context" in result
        assert result["events"][0]["event"] == "context_retrieval_completed"

    @pytest.mark.asyncio
    async def test_empty_issue_key(self):
        """Empty string issue_key is treated as missing."""
        result = await retrieve_context_node({"issue_key": ""})
        assert result["error"] == "issue_key is required for context retrieval"

    @pytest.mark.asyncio
    @patch("agentic_devtools.context.nodes.IssueContextRetriever")
    async def test_default_affected_paths(self, mock_retriever_cls, monkeypatch, tmp_path):
        """When affected_paths is not in state, defaults to empty list."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)
        monkeypatch.chdir(tmp_path)

        mock_ctx = MagicMock()
        mock_ctx.to_dict.return_value = {}
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=mock_ctx)
        mock_retriever_cls.return_value = mock_retriever

        await retrieve_context_node({"issue_key": "T-1"})

        mock_retriever.retrieve.assert_awaited_once_with("T-1", [])
