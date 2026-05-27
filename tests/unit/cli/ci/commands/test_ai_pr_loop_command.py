"""Tests for ai_pr_loop_command() CLI entry point."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import ai_pr_loop_command


class TestAIPRLoopCommand:
    """Tests for the ai_pr_loop_command CLI entry point."""

    def test_exits_zero_without_feature_flag(self) -> None:
        """Without feature flag, exits 0 to defer to legacy path."""
        with patch.dict(os.environ, {"AGDT_USE_PYTHON_ORCHESTRATOR": ""}, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 0

    def test_exits_zero_with_flag_set_to_zero(self) -> None:
        with patch.dict(os.environ, {"AGDT_USE_PYTHON_ORCHESTRATOR": "0"}, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 0

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_exits_10_without_event_vars(self, mock_which) -> None:
        """When GITHUB_EVENT_PATH not set, exits 10."""
        env = {"AGDT_USE_PYTHON_ORCHESTRATOR": "1", "GITHUB_EVENT_PATH": "", "GITHUB_EVENT_NAME": ""}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(SystemExit) as exc_info:
                ai_pr_loop_command()
            assert exc_info.value.code == 10

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_reads_event_file(self, mock_which) -> None:
        """Successfully reads and parses event file."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_loop:
                    with pytest.raises(SystemExit) as exc_info:
                        ai_pr_loop_command()
                    assert exc_info.value.code == 0
                    mock_loop.assert_called_once()
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_routes_to_pipeline_v2_when_enabled(self, mock_which) -> None:
        """Routes to run_ai_pr_loop_v2 when both feature flags are enabled."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "AGDT_USE_PIPELINE_V2": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_v1:
                    with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop_v2", return_value=0) as mock_v2:
                        with pytest.raises(SystemExit) as exc_info:
                            ai_pr_loop_command()
                        assert exc_info.value.code == 0
                        mock_v2.assert_called_once()
                        mock_v1.assert_not_called()
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_malformed_event_exits_2(self, mock_which) -> None:
        """Malformed event payload exits with code 2."""
        payload = {"invalid": "data"}  # Not a valid PR event
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    ai_pr_loop_command()
                assert exc_info.value.code == 2
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_invalid_json_file_exits_10(self, mock_which) -> None:
        """Invalid JSON in event file exits with code 10."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json{{{")
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    ai_pr_loop_command()
                assert exc_info.value.code == 10
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_body_only_edit_exits_zero(self, mock_which) -> None:
        """Body-only edited event exits 0 without calling orchestrator."""
        payload = {
            "action": "edited",
            "changes": {"body": {"from": "old body"}},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_loop:
                    with pytest.raises(SystemExit) as exc_info:
                        ai_pr_loop_command()
                    assert exc_info.value.code == 0
                    mock_loop.assert_not_called()
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_body_only_edit_exits_zero_for_pipeline_v2(self, mock_which) -> None:
        """Body-only edited event exits 0 without calling pipeline v2."""
        payload = {
            "action": "edited",
            "changes": {"body": {"from": "old body"}},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "AGDT_USE_PIPELINE_V2": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_v1:
                    with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop_v2", return_value=0) as mock_v2:
                        with pytest.raises(SystemExit) as exc_info:
                            ai_pr_loop_command()
                        assert exc_info.value.code == 0
                        mock_v2.assert_not_called()
                        mock_v1.assert_not_called()
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_title_edit_proceeds_to_orchestrator(self, mock_which) -> None:
        """Edited event with title change proceeds to orchestrator."""
        payload = {
            "action": "edited",
            "changes": {"title": {"from": "[WIP] Old Title"}},
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_loop:
                    with pytest.raises(SystemExit) as exc_info:
                        ai_pr_loop_command()
                    assert exc_info.value.code == 0
                    mock_loop.assert_called_once()
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_non_edited_event_proceeds_to_orchestrator(self, mock_which) -> None:
        """Non-edited events are not affected by the edit-relevance guard."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "head": {"ref": "feature/test", "sha": "abc123"},
                "base": {"ref": "main"},
            },
            "repository": {"full_name": "owner/repo"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_loop:
                    with pytest.raises(SystemExit) as exc_info:
                        ai_pr_loop_command()
                    assert exc_info.value.code == 0
                    mock_loop.assert_called_once()
        finally:
            os.unlink(event_path)
