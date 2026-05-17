"""Tests for speckit_trigger_command() CLI entry point."""

import json
import os
import subprocess
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
    @patch("agentic_devtools.cli.ci.commands.process_speckit_label_event", return_value=0)
    def test_processes_label_event(self, mock_process, mock_which) -> None:
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
                assert exc_info.value.code == 0
            mock_process.assert_called_once()
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

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("agentic_devtools.cli.ci.commands.run_safe")
    @patch("agentic_devtools.cli.ci.commands.process_speckit_label_event", return_value=0)
    def test_workflow_dispatch_fetches_issue_and_processes(self, mock_process, mock_run_safe, mock_which) -> None:
        """workflow_dispatch fetches issue via gh api and calls process_speckit_label_event."""
        issue_data = {"number": 42, "title": "Feature", "body": "Do it", "labels": [{"name": "enhancement"}]}
        mock_run_safe.return_value = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout=json.dumps(issue_data), stderr=""
        )
        payload = {"inputs": {"issue_number": "42"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "owner/repo",
                "SPECKIT_TRIGGER_LABEL": "speckit",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 0
            mock_process.assert_called_once()
            # Verify EventPayload was constructed with action=labeled and trigger_label=speckit
            call_args = mock_process.call_args[0]
            event_payload = call_args[1]
            assert event_payload.action == "labeled"
            assert event_payload.trigger_label == "speckit"
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("agentic_devtools.cli.ci.commands.run_safe")
    def test_workflow_dispatch_exits_10_when_issue_payload_invalid_json(self, mock_run_safe, mock_which) -> None:
        """workflow_dispatch exits 10 when fetched issue payload is not valid JSON."""
        mock_run_safe.return_value = subprocess.CompletedProcess(args=["gh"], returncode=0, stdout="not-json", stderr="")
        payload = {"inputs": {"issue_number": "42"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 10
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("agentic_devtools.cli.ci.commands.process_speckit_label_event", return_value=0)
    @patch("agentic_devtools.cli.ci.commands.run_safe")
    def test_workflow_dispatch_ignores_synthetic_cleanup_errors(
        self,
        mock_run_safe,
        mock_process,
        mock_which,
    ) -> None:
        issue_data = {"number": 42, "title": "Feature", "body": "Do it", "labels": [{"name": "enhancement"}]}
        mock_run_safe.return_value = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout=json.dumps(issue_data), stderr=""
        )
        payload = {"inputs": {"issue_number": "42"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with patch("agentic_devtools.cli.ci.commands.os.unlink", side_effect=OSError("cannot delete")) as mock_unlink:
                    with pytest.raises(SystemExit) as exc_info:
                        speckit_trigger_command()
                assert exc_info.value.code == 0
            mock_process.assert_called_once()
            mock_unlink.assert_called()
        finally:
            os.remove(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_workflow_dispatch_exits_2_when_no_issue_number(self, mock_which) -> None:
        """workflow_dispatch without issue_number input exits with code 2."""
        payload = {"inputs": {}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 2
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("agentic_devtools.cli.ci.commands.run_safe")
    def test_workflow_dispatch_exits_10_when_gh_api_fails(self, mock_run_safe, mock_which) -> None:
        """workflow_dispatch exits 10 when gh api fails to fetch issue."""
        mock_run_safe.return_value = subprocess.CompletedProcess(
            args=["gh"], returncode=1, stdout="", stderr="Not Found"
        )
        payload = {"inputs": {"issue_number": "9999"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 10
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_workflow_dispatch_exits_2_when_issue_number_non_numeric(self, mock_which) -> None:
        """workflow_dispatch with non-numeric issue_number exits with code 2."""
        payload = {"inputs": {"issue_number": "abc"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "owner/repo",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 2
        finally:
            os.unlink(event_path)

    @patch("shutil.which", return_value="/usr/bin/gh")
    def test_workflow_dispatch_exits_10_when_repo_invalid(self, mock_which) -> None:
        """workflow_dispatch with invalid GITHUB_REPOSITORY exits with code 10."""
        payload = {"inputs": {"issue_number": "42"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            event_path = f.name

        try:
            env = {
                "AGDT_USE_PYTHON_ORCHESTRATOR": "1",
                "GITHUB_EVENT_PATH": event_path,
                "GITHUB_EVENT_NAME": "workflow_dispatch",
                "GITHUB_REPOSITORY": "",
            }
            with patch.dict(os.environ, env, clear=False):
                with pytest.raises(SystemExit) as exc_info:
                    speckit_trigger_command()
                assert exc_info.value.code == 10
        finally:
            os.unlink(event_path)
