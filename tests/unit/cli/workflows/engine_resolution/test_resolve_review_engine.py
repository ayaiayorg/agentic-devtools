"""Tests for resolve_review_engine function."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.engine_resolution import (
    DEFAULT_ENGINE,
    ENGINE_ENV_VAR,
    resolve_review_engine,
)


class TestResolveReviewEngine:
    """Tests for resolve_review_engine priority logic."""

    def test_returns_default_when_nothing_provided(self):
        """Returns 'default' when no CLI, state, or env is set."""
        with patch.dict(os.environ, {}, clear=True):
            assert resolve_review_engine() == DEFAULT_ENGINE

    def test_cli_flag_takes_highest_priority(self):
        """CLI flag overrides state and env."""
        with patch.dict(os.environ, {ENGINE_ENV_VAR: "default"}):
            result = resolve_review_engine(
                cli_flag="langchain",
                state_key="default",
                env_var="default",
            )
            assert result == "langchain"

    def test_state_key_overrides_env(self):
        """State key has priority over environment variable."""
        result = resolve_review_engine(
            cli_flag=None,
            state_key="langchain",
            env_var="default",
        )
        assert result == "langchain"

    def test_env_var_used_when_no_cli_or_state(self):
        """Environment variable is used as fallback."""
        result = resolve_review_engine(
            cli_flag=None,
            state_key=None,
            env_var="langchain",
        )
        assert result == "langchain"

    def test_reads_os_environ_when_env_var_param_is_none(self):
        """When env_var param is None, reads from os.environ."""
        with patch.dict(os.environ, {ENGINE_ENV_VAR: "langchain"}):
            result = resolve_review_engine(cli_flag=None, state_key=None)
            assert result == "langchain"

    def test_invalid_engine_exits(self):
        """Invalid engine value triggers sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            resolve_review_engine(cli_flag="invalid_engine")
        assert exc_info.value.code == 1

    def test_whitespace_is_stripped(self):
        """Leading/trailing whitespace in values is stripped."""
        result = resolve_review_engine(cli_flag="  langchain  ")
        assert result == "langchain"

    def test_case_insensitive(self):
        """Engine values are case-insensitive."""
        result = resolve_review_engine(cli_flag="LangChain")
        assert result == "langchain"

    def test_empty_string_cli_flag_falls_through(self):
        """Empty string CLI flag falls through to state/env/default."""
        result = resolve_review_engine(cli_flag="", state_key="langchain")
        assert result == "langchain"

    def test_empty_env_var_falls_to_default(self):
        """Empty environment variable value falls to default."""
        result = resolve_review_engine(cli_flag=None, state_key=None, env_var="")
        assert result == DEFAULT_ENGINE

    def test_whitespace_only_state_value_falls_through_to_env(self):
        """Whitespace-only state value is treated as empty."""
        result = resolve_review_engine(
            cli_flag=None,
            state_key="   ",
            env_var="langchain",
        )
        assert result == "langchain"

    def test_uppercase_state_value_is_normalized(self):
        """Uppercase state value is normalized to lowercase engine."""
        result = resolve_review_engine(
            cli_flag=None,
            state_key="LANGCHAIN",
            env_var="default",
        )
        assert result == "langchain"
