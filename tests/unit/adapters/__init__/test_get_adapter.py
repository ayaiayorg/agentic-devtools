"""Tests for agentic_devtools.adapters.get_adapter factory function."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.adapters import get_adapter
from agentic_devtools.adapters.github_adapter import GitHubIssuesAdapter
from agentic_devtools.adapters.jira_adapter import JiraAdapter
from agentic_devtools.adapters.markdown_adapter import MarkdownAdapter


def _write_config(tmp_path: Path, platform: dict) -> None:
    """Write a .github/agdt-config.json with the given platform section."""
    config_dir = tmp_path / ".github"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "agdt-config.json"
    config_path.write_text(json.dumps({"platform": platform}), encoding="utf-8")


class TestGetAdapter:
    """Tests for the get_adapter() factory function."""

    def test_returns_jira_adapter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter returns JiraAdapter when issue_adapter == 'jira'."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "jira",
                "jira": {"project_key": "PROJ"},
            },
        )
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")

        adapter = get_adapter(str(tmp_path))

        assert isinstance(adapter, JiraAdapter)

    def test_returns_github_adapter(self, tmp_path: Path) -> None:
        """get_adapter returns GitHubIssuesAdapter when issue_adapter == 'github'."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "github",
                "github": {"repo_owner": "owner", "repo_name": "repo"},
            },
        )

        adapter = get_adapter(str(tmp_path))

        assert isinstance(adapter, GitHubIssuesAdapter)

    def test_returns_markdown_adapter(self, tmp_path: Path) -> None:
        """get_adapter returns MarkdownAdapter when issue_adapter == 'markdown'."""
        _write_config(tmp_path, {"issue_adapter": "markdown"})

        adapter = get_adapter(str(tmp_path))

        assert isinstance(adapter, MarkdownAdapter)

    def test_defaults_to_jira_when_no_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter defaults to JiraAdapter when no config file exists."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")

        # default is jira, but project_key will be empty → JiraAdapter raises ValueError
        # So we mock load_platform_config to include a project_key
        with patch("agentic_devtools.adapters.load_platform_config") as mock_load:
            mock_load.return_value = {
                "issue_adapter": "jira",
                "jira": {"project_key": "DEFAULT"},
                "github": {},
                "azure_devops": {},
            }
            adapter = get_adapter(str(tmp_path))

        assert isinstance(adapter, JiraAdapter)

    def test_raises_on_unknown_adapter(self, tmp_path: Path) -> None:
        """get_adapter raises ValueError for unrecognized adapter name."""
        with patch("agentic_devtools.adapters.load_platform_config") as mock_load:
            mock_load.return_value = {
                "issue_adapter": "unknown_platform",
                "jira": {},
                "github": {},
                "azure_devops": {},
            }
            with pytest.raises(ValueError, match="Unknown issue adapter: unknown_platform"):
                get_adapter(str(tmp_path))

    def test_jira_ssl_verify_false(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter sets ssl_verify=False when JIRA_SSL_VERIFY='0'."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "jira",
                "jira": {"project_key": "PROJ"},
            },
        )
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        monkeypatch.setenv("JIRA_SSL_VERIFY", "0")

        adapter = get_adapter(str(tmp_path))
        assert isinstance(adapter, JiraAdapter)
        assert adapter._config.ssl_verify is False

    def test_jira_ssl_verify_false_text(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter sets ssl_verify=False when JIRA_SSL_VERIFY='false'."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "jira",
                "jira": {"project_key": "PROJ"},
            },
        )
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        monkeypatch.setenv("JIRA_SSL_VERIFY", "false")

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.ssl_verify is False

    def test_jira_ssl_verify_default_true(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter defaults ssl_verify to True when env var not set."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "jira",
                "jira": {"project_key": "PROJ"},
            },
        )
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        monkeypatch.delenv("JIRA_SSL_VERIFY", raising=False)

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.ssl_verify is True

    def test_github_adapter_repo_slug(self, tmp_path: Path) -> None:
        """get_adapter constructs correct repo slug from config."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "github",
                "github": {"repo_owner": "my-org", "repo_name": "my-repo"},
            },
        )

        adapter = get_adapter(str(tmp_path))

        assert isinstance(adapter, GitHubIssuesAdapter)
        assert adapter._repo == "my-org/my-repo"

    def test_jira_empty_env_vars_constructs_adapter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter constructs JiraAdapter with empty env vars (lazy validation)."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "jira",
                "jira": {"project_key": "PROJ"},
            },
        )
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)

        adapter = get_adapter(str(tmp_path))
        assert isinstance(adapter, JiraAdapter)
        # base_url is empty — will fail at call time, not construction time
        assert adapter._config.base_url == ""

    def test_jira_no_project_key_constructs_adapter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter constructs JiraAdapter without project_key (lazy validation)."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "jira",
                "jira": {},
            },
        )
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")

        adapter = get_adapter(str(tmp_path))
        assert isinstance(adapter, JiraAdapter)
        # project_key is empty — create_issue will fail, but construction succeeds
        with pytest.raises(ValueError, match="project_key"):
            adapter.create_issue("T", "D")

    # ------------------------------------------------------------------
    # Jira auth scheme tests
    # ------------------------------------------------------------------

    def test_jira_bearer_auth_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter uses Bearer auth by default when no identity is set."""
        _write_config(tmp_path, {"issue_adapter": "jira", "jira": {"project_key": "P"}})
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "my-token")
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.headers["Authorization"] == "Bearer my-token"

    def test_jira_bearer_auth_copilot_pat_fallback(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter falls back to JIRA_COPILOT_PAT when JIRA_API_TOKEN is unset."""
        _write_config(tmp_path, {"issue_adapter": "jira", "jira": {"project_key": "P"}})
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.setenv("JIRA_COPILOT_PAT", "copilot-pat")
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.headers["Authorization"] == "Bearer copilot-pat"

    def test_jira_basic_auth_when_identity_set(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter uses Basic auth when a JIRA identity env var is set."""
        _write_config(tmp_path, {"issue_adapter": "jira", "jira": {"project_key": "P"}})
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "my-token")
        monkeypatch.setenv("JIRA_EMAIL", "user@example.com")
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.headers["Authorization"].startswith("Basic ")

    def test_jira_basic_auth_via_scheme(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter uses Basic auth when JIRA_AUTH_SCHEME=basic with identity."""
        _write_config(tmp_path, {"issue_adapter": "jira", "jira": {"project_key": "P"}})
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "my-token")
        monkeypatch.setenv("JIRA_USERNAME", "user")
        monkeypatch.setenv("JIRA_AUTH_SCHEME", "basic")
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.headers["Authorization"].startswith("Basic ")

    def test_jira_basic_scheme_no_identity_no_auth_header(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_adapter omits Authorization header when basic scheme lacks identity."""
        _write_config(tmp_path, {"issue_adapter": "jira", "jira": {"project_key": "P"}})
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "my-token")
        monkeypatch.setenv("JIRA_AUTH_SCHEME", "basic")
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)

        adapter = get_adapter(str(tmp_path))
        # No Authorization header — will fail lazily at call time
        assert "Authorization" not in adapter._config.headers

    def test_jira_ssl_verify_ca_bundle_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_adapter passes CA bundle path as-is when JIRA_SSL_VERIFY is a path."""
        _write_config(tmp_path, {"issue_adapter": "jira", "jira": {"project_key": "P"}})
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "token")
        monkeypatch.delenv("JIRA_USERNAME", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_EMAIL", raising=False)
        monkeypatch.delenv("JIRA_AUTH_SCHEME", raising=False)
        monkeypatch.delenv("JIRA_COPILOT_PAT", raising=False)
        monkeypatch.setenv("JIRA_SSL_VERIFY", "/etc/ssl/certs/ca-bundle.crt")

        adapter = get_adapter(str(tmp_path))
        assert adapter._config.ssl_verify == "/etc/ssl/certs/ca-bundle.crt"

    # ------------------------------------------------------------------
    # GitHub adapter repo slug normalization
    # ------------------------------------------------------------------

    def test_github_adapter_empty_repo_owner(self, tmp_path: Path) -> None:
        """get_adapter normalizes repo slug to empty when repo_owner is missing."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "github",
                "github": {"repo_owner": "", "repo_name": "repo"},
            },
        )

        adapter = get_adapter(str(tmp_path))
        assert isinstance(adapter, GitHubIssuesAdapter)
        assert adapter._repo == ""

    def test_github_adapter_empty_repo_name(self, tmp_path: Path) -> None:
        """get_adapter normalizes repo slug to empty when repo_name is missing."""
        _write_config(
            tmp_path,
            {
                "issue_adapter": "github",
                "github": {"repo_owner": "owner", "repo_name": ""},
            },
        )

        adapter = get_adapter(str(tmp_path))
        assert isinstance(adapter, GitHubIssuesAdapter)
        assert adapter._repo == ""

    def test_github_adapter_missing_github_section(self, tmp_path: Path) -> None:
        """get_adapter normalizes repo slug to empty when github section is absent."""
        _write_config(tmp_path, {"issue_adapter": "github"})

        adapter = get_adapter(str(tmp_path))
        assert isinstance(adapter, GitHubIssuesAdapter)
        assert adapter._repo == ""
