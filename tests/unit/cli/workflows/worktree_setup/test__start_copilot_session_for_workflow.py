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


def _patch_no_tty(monkeypatch):
    """Patch sys.stdin and sys.stdout to report no TTY attached."""
    mock_stdin = MagicMock()
    mock_stdin.isatty.return_value = False
    mock_stdout = MagicMock()
    mock_stdout.isatty.return_value = False
    monkeypatch.setattr("sys.stdin", mock_stdin)
    monkeypatch.setattr("sys.stdout", mock_stdout)


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
            model=None,
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
            model=None,
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
            model=None,
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
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_restores_env_when_chdir_raises(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Verify env var is restored when os.chdir(worktree_path) raises."""
        import pytest

        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        mock_vscode.return_value = True

        original_cwd = os.getcwd()
        original_state_dir = "/original/safe/dir"
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", original_state_dir)

        # Patch os.chdir to raise on the worktree path but allow the
        # finally-block restore to succeed.
        real_chdir = os.chdir

        def chdir_side_effect(path):
            if path == str(tmp_path):
                raise FileNotFoundError(f"No such directory: {path}")
            return real_chdir(path)

        with pytest.raises(FileNotFoundError):
            with patch("os.chdir", side_effect=chdir_side_effect):
                _start_copilot_session_for_workflow(
                    worktree_path=str(tmp_path),
                    prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                    start_prompt=_CUSTOM_START_PROMPT,
                    workflow_name=_CUSTOM_WORKFLOW_NAME,
                )

        # Env var and CWD must be restored despite the chdir failure
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
        """Verify True is returned when auto-start task run ID appears in state."""
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

        _patch_no_tty(monkeypatch)

        run_id = "test-auto-run-123"

        # Simulate run ID appearing in state during the wait loop
        def mark_run_triggered_on_sleep(_duration):
            # Write the run ID into state to simulate the VS Code task firing
            state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / "state.json"
            state = {"copilot": {"auto_start_triggered_runs": [run_id]}}
            state_file.write_text(json.dumps(state), encoding="utf-8")

        with patch("time.sleep", side_effect=mark_run_triggered_on_sleep):
            with patch(
                "agentic_devtools.state.get_state_file_path",
                return_value=tmp_path / ".agdt" / "workflows" / "_test" / "_test" / "state.json",
            ):
                with patch("agentic_devtools.state.get_value", return_value=run_id):
                    result = _start_copilot_session_for_workflow(
                        worktree_path=str(tmp_path),
                        prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                        start_prompt=_CUSTOM_START_PROMPT,
                        workflow_name=_CUSTOM_WORKFLOW_NAME,
                        interactive=True,
                    )

        assert result is True
        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_run_id_check_runs_when_not_interactive(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Run-ID check runs even when interactive=False, so VS Code auto-start is detected."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        # Write a tasks.json with the auto-start task (simulating successful injection)
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        _patch_no_tty(monkeypatch)

        run_id = "test-auto-run-456"

        # Simulate run ID appearing during wait loop
        def mark_run_triggered_on_sleep(_duration):
            state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / "state.json"
            state = {"copilot": {"auto_start_triggered_runs": [run_id]}}
            state_file.write_text(json.dumps(state), encoding="utf-8")

        with patch("time.sleep", side_effect=mark_run_triggered_on_sleep):
            with patch(
                "agentic_devtools.state.get_state_file_path",
                return_value=tmp_path / ".agdt" / "workflows" / "_test" / "_test" / "state.json",
            ):
                with patch("agentic_devtools.state.get_value", return_value=run_id):
                    result = _start_copilot_session_for_workflow(
                        worktree_path=str(tmp_path),
                        prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                        start_prompt=_CUSTOM_START_PROMPT,
                        workflow_name=_CUSTOM_WORKFLOW_NAME,
                        interactive=False,  # Key: interactive=False must not skip run-ID check
                    )

        # VS Code confirmed via run ID in state — no background session started
        assert result is True
        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_fallback_session_when_no_auto_start_task_not_interactive(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When interactive=False and no auto-start task in tasks.json, session is started as fallback."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        # No tasks.json → injection never happened (or failed)

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=False,
            )

        # Fallback: session started by the background process
        assert result is True
        mock_copilot.assert_called_once_with(
            prompt=_CUSTOM_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
            model=None,
        )

    # ------------------------------------------------------------------
    # Edge-case coverage for the auto-start task / sentinel logic
    # ------------------------------------------------------------------

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_tasks_key_not_a_list_falls_through(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When tasks.json has a non-list 'tasks' key, the auto-start check falls through."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {"version": "2.0.0", "tasks": "not-a-list"}
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        _patch_no_tty(monkeypatch)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=False,
            )

        assert result is True
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_tasks_json_not_a_dict_falls_through(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When tasks.json contains a non-dict (e.g. list), the auto-start check falls through."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        # Write a JSON list instead of an object
        (vscode_dir / "tasks.json").write_text("[]", encoding="utf-8")

        _patch_no_tty(monkeypatch)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=False,
            )

        assert result is True
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_pre_existing_triggered_run_id_falls_through_to_background(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Pre-existing triggered run ID causes fallback to background Copilot session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        run_id = "already-triggered-run"

        # Create state with run ID already triggered
        state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "state.json"
        state = {"copilot": {"auto_start_triggered_runs": [run_id]}}
        state_file.write_text(json.dumps(state), encoding="utf-8")

        _patch_no_tty(monkeypatch)

        with patch("agentic_devtools.state.get_state_file_path", return_value=state_file):
            with patch("agentic_devtools.state.get_value", return_value=run_id):
                with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
                    result = _start_copilot_session_for_workflow(
                        worktree_path=str(tmp_path),
                        prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                        start_prompt=_CUSTOM_START_PROMPT,
                        workflow_name=_CUSTOM_WORKFLOW_NAME,
                        interactive=False,
                    )

        assert result is True
        # Falls through to background session because run ID was already triggered
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_run_id_timeout_falls_through_to_background(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When the run ID never appears in state, the function falls through to a background session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        _patch_no_tty(monkeypatch)

        # Create empty state file (run ID never appears)
        state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "state.json"
        state_file.write_text("{}", encoding="utf-8")

        with patch("time.sleep"):
            with patch("agentic_devtools.state.get_state_file_path", return_value=state_file):
                with patch("agentic_devtools.state.get_value", return_value="some-run-id"):
                    with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
                        result = _start_copilot_session_for_workflow(
                            worktree_path=str(tmp_path),
                            prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                            start_prompt=_CUSTOM_START_PROMPT,
                            workflow_name=_CUSTOM_WORKFLOW_NAME,
                            interactive=False,
                        )

        assert result is True
        # Run ID never appeared — falls through to background session
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_invalid_tasks_json_falls_through(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Malformed tasks.json is silently ignored, falling through to background session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text("not valid json!!!", encoding="utf-8")

        _patch_no_tty(monkeypatch)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=False,
            )

        assert result is True
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_auto_start_wait_resolves_state_in_target_worktree(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Auto-start confirmation resolves state using the target worktree context."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        monkeypatch.chdir(outside_dir)
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "wrong-state-dir")
        _patch_no_tty(monkeypatch)

        run_id = "target-worktree-run-id"
        captured = {}

        def fake_get_state_file_path():
            captured["cwd"] = os.getcwd()
            captured["state_dir"] = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
            return tmp_path / ".agdt" / "workflows" / "_test" / "_test" / "state.json"

        def fake_get_value(key):
            assert key == "agdt_run_id"
            captured["value_cwd"] = os.getcwd()
            captured["value_state_dir"] = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
            return run_id

        def mark_run_triggered_on_sleep(_duration):
            state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
            state_dir.mkdir(parents=True, exist_ok=True)
            state_file = state_dir / "state.json"
            state = {"copilot": {"auto_start_triggered_runs": [run_id]}}
            state_file.write_text(json.dumps(state), encoding="utf-8")

        with patch("time.sleep", side_effect=mark_run_triggered_on_sleep):
            with patch("agentic_devtools.state.get_state_file_path", side_effect=fake_get_state_file_path):
                with patch("agentic_devtools.state.get_value", side_effect=fake_get_value):
                    result = _start_copilot_session_for_workflow(
                        worktree_path=str(tmp_path),
                        prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                        start_prompt=_CUSTOM_START_PROMPT,
                        workflow_name=_CUSTOM_WORKFLOW_NAME,
                        interactive=False,
                    )

        assert result is True
        assert captured == {
            "cwd": str(tmp_path),
            "state_dir": None,
            "value_cwd": str(tmp_path),
            "value_state_dir": None,
        }
        assert os.getcwd() == str(outside_dir)
        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "wrong-state-dir"
        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_auto_start_wait_falls_through_when_state_resolution_fails(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """State-resolution failures in the wait branch fall through to the background session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        _patch_no_tty(monkeypatch)

        with patch("agentic_devtools.state.get_state_file_path", side_effect=RuntimeError("boom")):
            with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
                result = _start_copilot_session_for_workflow(
                    worktree_path=str(tmp_path),
                    prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                    start_prompt=_CUSTOM_START_PROMPT,
                    workflow_name=_CUSTOM_WORKFLOW_NAME,
                    interactive=False,
                )

        assert result is True
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_prints_no_run_id_message_and_falls_through(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
        capsys,
    ):
        """When auto-start task exists but run ID is empty, prints fallback message and starts background session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup._resolve_state_context_in_worktree",
            return_value=(tmp_path / ".agdt" / "workflows" / "_test" / "_test" / "state.json", ""),
        ):
            with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
                result = _start_copilot_session_for_workflow(
                    worktree_path=str(tmp_path),
                    prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                    start_prompt=_CUSTOM_START_PROMPT,
                    workflow_name=_CUSTOM_WORKFLOW_NAME,
                    interactive=False,
                )

        assert result is True
        captured = capsys.readouterr()
        assert "no run ID is available in state" in captured.out
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_terminal_send_fallback_returns_true_skips_background_session(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When _try_terminal_send_fallback returns True, the non-interactive session is skipped."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        _patch_no_tty(monkeypatch)

        state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_file = state_dir / "state.json"
        state_file.write_text("{}", encoding="utf-8")

        with patch("time.sleep"):
            with patch("agentic_devtools.state.get_state_file_path", return_value=state_file):
                with patch("agentic_devtools.state.get_value", return_value="some-run-id"):
                    with patch(
                        "agentic_devtools.cli.workflows.worktree_setup._try_terminal_send_fallback",
                        return_value=True,
                    ):
                        result = _start_copilot_session_for_workflow(
                            worktree_path=str(tmp_path),
                            prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                            start_prompt=_CUSTOM_START_PROMPT,
                            workflow_name=_CUSTOM_WORKFLOW_NAME,
                            interactive=False,
                        )

        assert result is True
        # Fallback succeeded — non-interactive session must NOT be started
        mock_copilot.assert_not_called()

    # ------------------------------------------------------------------
    # autostart_injected=True: skip background fallback
    # ------------------------------------------------------------------

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_autostart_injected_skips_background_fallback(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When autostart_injected=True and no TTY, return True immediately without background session."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True
        _patch_no_tty(monkeypatch)

        result = _start_copilot_session_for_workflow(
            worktree_path=str(tmp_path),
            prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
            start_prompt=_CUSTOM_START_PROMPT,
            workflow_name=_CUSTOM_WORKFLOW_NAME,
            autostart_injected=True,
        )

        assert result is True
        # No background Copilot session started — VS Code handles it
        mock_copilot.assert_not_called()
        # Prompt file wait should still be called (early return is after prompt check)
        # but the key assertion is no background session was spawned

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_autostart_injected_does_not_skip_when_tty_attached(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When autostart_injected=True but TTY is attached, proceed normally (interactive session)."""
        _setup_prompt_file(tmp_path)
        mock_wait.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        with patch("agentic_devtools.state.get_state_dir", return_value=tmp_path):
            result = _start_copilot_session_for_workflow(
                worktree_path=str(tmp_path),
                prompt_file_relative_path=_CUSTOM_PROMPT_RELATIVE,
                start_prompt=_CUSTOM_START_PROMPT,
                workflow_name=_CUSTOM_WORKFLOW_NAME,
                interactive=True,
                autostart_injected=True,
            )

        # TTY attached means the user is in an interactive terminal — proceed normally
        assert result is True
        mock_copilot.assert_called_once()
