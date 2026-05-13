"""Tests for speckit_trigger_command() CLI entry point."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import speckit_trigger_command


class TestSpeckitTriggerCommand:
    """Tests for the speckit_trigger_command CLI entry point."""

    def test_exits_zero_without_feature_flag(self) -> None:
        with patch.dict(os.environ, {"AGDT_USE_PYTHON_ORCHESTRATOR": ""}, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                speckit_trigger_command()
            assert exc_info.value.code == 0

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_exits_10_without_event_vars(self, mock_which) -> None:
        env = {"AGDT_USE_PYTHON_ORCHESTRATOR": "1", "GITHUB_EVENT_PATH": "", "GITHUB_EVENT_NAME": ""}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                speckit_trigger_command()
            assert exc_info.value.code == 10

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_processes_label_event(self, mock_which) -> None:
        payload = {
            "action": "labeled",
            "label": {"name": "speckit-ready"},
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "issues",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 11
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value=None)
    def test_missing_gh_exits_10(self, mock_which) -> None:
        env = {"AGDT_USE_PYTHON_ORCHESTRATOR": "1"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                speckit_trigger_command()
            assert exc_info.value.code == 10

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_invalid_json_exits_10(self, mock_which) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "issues",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 10
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_malformed_event_exits_2(self, mock_which) -> None:
        """Unsupported event type exits with code 2."""
        payload = {"action": "deployed"}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "deployment",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 2
        finally:
            os.unlink(event_path)
