"""Tests for feature flag routing in CI commands."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import ai_pr_loop_command


class TestFeatureFlag:
    """Tests for AGDT_USE_PYTHON_ORCHESTRATOR feature flag."""

    def test_flag_unset_uses_legacy(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AGDT_USE_PYTHON_ORCHESTRATOR", None)
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 0

    def test_flag_zero_uses_legacy(self) -> None:
        with patch.dict(os.environ, {"AGDT_USE_PYTHON_ORCHESTRATOR": "0"}, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 0

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_flag_one_uses_python(self, mock_which) -> None:
        """Flag=1 attempts Python path (fails on missing env vars)."""
        env = {"AGDT_USE_PYTHON_ORCHESTRATOR": "1", "GITHUB_EVENT_PATH": "", "GITHUB_EVENT_NAME": ""}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            # Fails because event vars are missing, but it tried the Python path
            assert exc_info.value.code == 10

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_flag_true_uses_python(self, mock_which) -> None:
        """Flag=true (case-insensitive) uses Python path."""
        env = {"AGDT_USE_PYTHON_ORCHESTRATOR": "TRUE", "GITHUB_EVENT_PATH": "", "GITHUB_EVENT_NAME": ""}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 10
