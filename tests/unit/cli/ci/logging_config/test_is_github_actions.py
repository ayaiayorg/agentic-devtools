"""Tests for is_github_actions() helper."""

import os
from unittest.mock import patch

from agentic_devtools.cli.ci.logging_config import is_github_actions


class TestIsGithubActions:
    """Tests for is_github_actions()."""

    def test_returns_true_when_env_set(self) -> None:
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            assert is_github_actions() is True

    def test_returns_false_when_env_false(self) -> None:
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            assert is_github_actions() is False

    def test_returns_false_when_env_absent(self) -> None:
        env = os.environ.copy()
        env.pop("GITHUB_ACTIONS", None)
        with patch.dict(os.environ, env, clear=True):
            assert is_github_actions() is False
