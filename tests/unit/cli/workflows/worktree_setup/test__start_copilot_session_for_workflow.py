"""Tests for _start_copilot_session_for_workflow."""

import json
import os
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _AUTO_START_TASK_LABEL,
    _start_copilot_session_for_workflow,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CUSTOM_PROMPT_RELATIVE = "custom/prompts/my-workflow-prompt.md"
_CUSTOM_START_PROMPT = "You are reviewing code. Run agdt-advance-workflow my-step now."
_CUSTOM_WORKFLOW_NAME = "my-custom-workflow"


def _setup_prompt_file(tmp_path, relative_path=_CUSTOM_PROMPT_RELATIVE, content="# Prompt"):
    """Create the prompt file under tmp_path and return its absolute path."""
    prompt_file = tmp_path / relative_path
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(content, encoding="utf-8")
    return prompt_file


class TestStartCopilotSessionForWorkflow:
    """Tests for the generic _start_copilot_session_for_workflow helper."""

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_uses_custom_prompt_file_path(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Verify the prompt file path is constructed from the parameter, not hardcoded."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
            )

        # _wait_for_prompt_file is called with the joined path
        expected_path = tmp_path / _CUSTOM_PROMPT_RELATIVE
        mock_wait.assert_called_once_with(expected_path)

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_uses_custom_start_prompt(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Verify the start_prompt parameter is passed to start_copilot_session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
            )

        mock_copilot.assert_called_once()
        assert mock_copilot.call_args[1]["prompt"] == _CUSTOM_START_PROMPT

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_workflow_name_in_log_output(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Verify workflow_name appears in printed messages."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
            )

        captured = capsys.readouterr()
        assert _CUSTOM_WORKFLOW_NAME in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_uses_get_state_dir_for_env_var(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify get_state_dir() is called and its result is used for AGENTIC_DEVTOOLS_STATE_DIR."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        resolved_state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        resolved_state_dir.mkdir(parents=True, exist_ok=True)

        captured_state_dir = []

        def capture_env(**_kwargs):
            captured_state_dir.append(os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"))

        mock_copilot.side_effect = capture_env
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)

        mock_get_state_dir = MagicMock(return_value=resolved_state_dir)
        with patch("agentic_devtools.state.get_state_dir", mock_get_state_dir):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
            )

        mock_get_state_dir.assert_called_once()
        assert captured_state_dir == [str(resolved_state_dir)]

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_returns_true_on_successful_session(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Verify True is returned when start_copilot_session succeeds."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
            )

        assert result is True

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_returns_false_when_prompt_file_not_found(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
    ):
        """Verify False is returned when prompt file wait times out."""
        mock_wait.return_value = False

        result = _start_copilot_session_for_workflow(
            worktree_path=str(tmp_path),
            prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
            start_prompt=_CUSTOM_START_PROMPT,
            workflow_name=_CUSTOM_WORKFLOW_NAME,
        )

        assert result is False
        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_returns_false_when_prompt_path_is_directory(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Verify False is returned when prompt path is a directory."""
        # Create as directory instead of file
        prompt_dir = tmp_path / _CUSTOM_PROMPT_RELATIVE
        prompt_dir.mkdir(parents=True)
        mock_wait.return_value = True

        result = _start_copilot_session_for_workflow(
            worktree_path=str(tmp_path),
            prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
            start_prompt=_CUSTOM_START_PROMPT,
            workflow_name=_CUSTOM_WORKFLOW_NAME,
        )

        assert result is False
        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "not a regular file" in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_interactive_session_with_tty_and_vscode(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify interactive mode works when TTY and VS Code are available."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=True,
            )

        mock_copilot.assert_called_once_with(
            prompt=_CUSTOM_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=True,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_forces_non_interactive_when_vscode_unavailable(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Verify session is non-interactive when VS Code is unavailable."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = False

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=True,
            )

        mock_copilot.assert_called_once_with(
            prompt=_CUSTOM_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_forces_non_interactive_when_no_tty(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify session is non-interactive when no TTY is attached."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=True,
            )

        mock_copilot.assert_called_once_with(
            prompt=_CUSTOM_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_sets_and_restores_state_dir_env(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify AGENTIC_DEVTOOLS_STATE_DIR is set during session and restored after."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        resolved_state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        resolved_state_dir.mkdir(parents=True, exist_ok=True)

        captured_state_dir = []

        def capture_env(**_kwargs):
            captured_state_dir.append(os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"))

        mock_copilot.side_effect = capture_env
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)

        with patch("agentic_devtools.state.get_state_dir", return_value=resolved_state_dir):
            _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
            )

        assert captured_state_dir == [str(resolved_state_dir)]
        assert "AGENTIC_DEVTOOLS_STATE_DIR" not in os.environ

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_restores_env_on_exception(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify env var and CWD are restored even when start_copilot_session raises."""
        import pytest

        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        original_cwd = os.getcwd()
        original_state_dir = "/original/safe/dir"
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", original_state_dir)

        mock_copilot.side_effect = RuntimeError("session failed")

        resolved_state_dir = tmp_path / ".agdt" / "state"
        resolved_state_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(RuntimeError, match="session failed"):
            with patch("agentic_devtools.state.get_state_dir", return_value=resolved_state_dir):
                _start_copilot_session_for_workflow(
                    worktree_path=str(tmp_path),
                    prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                    start_prompt=_CUSTOM_START_PROMPT,
                    workflow_name=_CUSTOM_WORKFLOW_NAME,
                )

        # Env var and CWD must be restored despite the exception
        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == original_state_dir
        assert os.getcwd() == original_cwd

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_returns_true_when_auto_start_task_confirmed(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify True is returned when auto-start task sentinel appears."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        # Write a tasks.json with the auto-start task
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        sentinel_dir = tmp_path / ".agdt"

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        # Simulate sentinel appearing during wait loop
        def create_sentinel_on_sleep(_duration):
            sentinel_dir.mkdir(parents=True, exist_ok=True)
            (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")

        with patch("time.sleep", side_effect=create_sentinel_on_sleep):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=True,
            )

        assert result is True
        mock_copilot.assert_not_called()
