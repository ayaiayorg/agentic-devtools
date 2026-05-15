"""Tests for feature flag routing in CI commands."""

import os
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import ai_pr_loop_command


class TestFeatureFlag:
    """Tests for AGDT_USE_PYTHON_ORCHESTRATOR feature flag."""

    @pytest.mark.parametrize("flag_value", [None, "0"])
    def test_unset_or_zero_uses_legacy_path(self, flag_value: str | None) -> None:
        env = {}
        if flag_value is not None:
            env["AGDT_USE_PYTHON_ORCHESTRATOR"] = flag_value

        with patch.dict(os.environ, env, clear=True):
            with patch("shutil.which") as mock_which:
                with pytest.raises(SystemExit) as exc_info:
                    ai_pr_loop_command()
                assert exc_info.value.code == 0
                mock_which.assert_not_called()

    @pytest.mark.parametrize("flag_value", ["1", "TRUE"])
    def test_one_or_true_selects_python_path(self, flag_value: str) -> None:
        env = {
            "AGDT_USE_PYTHON_ORCHESTRATOR": flag_value,
            "GITHUB_EVENT_PATH": "",
            "GITHUB_EVENT_NAME": "",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("shutil.which", return_value="/usr/bin/gh") as mock_which:
                with pytest.raises(SystemExit) as exc_info:
                    ai_pr_loop_command()
                assert exc_info.value.code == 10
                mock_which.assert_called_once_with("gh")
