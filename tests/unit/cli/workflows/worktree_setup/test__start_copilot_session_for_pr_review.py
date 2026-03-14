"""Tests for StartCopilotSessionForPrReview."""

import json
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _AUTO_START_TASK_LABEL,
    COPILOT_SESSION_START_PROMPT,
    _start_copilot_session_for_pr_review,
)


class TestStartCopilotSessionForPrReview:
    """Tests for _start_copilot_session_for_pr_review function."""

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_starts_interactive_session_when_vscode_available(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        capsys,
        monkeypatch,
    ):
        """Test that an interactive Copilot session is started when VS Code is available and a TTY is attached."""
        from unittest.mock import MagicMock

        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt content", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        # Simulate a real TTY so effective_interactive stays True
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        mock_copilot.assert_called_once_with(
            prompt=COPILOT_SESSION_START_PROMPT,
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
        """Test that session is non-interactive when VS Code is not available."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = False  # VS Code not available

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # interactive=False because VS Code is unavailable
        mock_copilot.assert_called_once_with(
            prompt=COPILOT_SESSION_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_uses_static_prompt_not_file_content(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that the static COPILOT_SESSION_START_PROMPT is used, not the rendered template file content."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# This content should NOT be used", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=False)

        # The prompt passed to start_copilot_session should be the static constant,
        # not the file content
        mock_copilot.assert_called_once_with(
            prompt=COPILOT_SESSION_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_skips_session_when_prompt_file_not_found(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that the Copilot session is skipped when the prompt file never appears."""
        mock_wait.return_value = False  # File never appeared

        _start_copilot_session_for_pr_review(str(tmp_path))

        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "Skipping Copilot session" in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_skips_session_when_prompt_path_is_directory(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        capsys,
    ):
        """Test that the Copilot session is skipped when the prompt path exists but is a directory."""
        # Create a directory where the prompt file is expected
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file_path = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file_path.mkdir()  # Create as a directory, not a file

        mock_wait.return_value = True  # exists() returns True for directories

        _start_copilot_session_for_pr_review(str(tmp_path))

        mock_copilot.assert_not_called()
        captured = capsys.readouterr()
        assert "not a regular file" in captured.out
        assert "Skipping Copilot session" in captured.out

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_uses_worktree_path_for_prompt_file_wait(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Test that the prompt file wait uses the worktree path."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review(str(tmp_path))

        mock_copilot.assert_called_once()
        call_kwargs = mock_copilot.call_args[1]
        assert call_kwargs["prompt"] == COPILOT_SESSION_START_PROMPT

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_sets_state_dir_env_and_restores_on_exit(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Test that AGENTIC_DEVTOOLS_STATE_DIR is set to the worktree during the session."""
        import os

        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        captured_state_dir: list = []

        def capture_env(**_kwargs):
            captured_state_dir.append(os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"))

        mock_copilot.side_effect = capture_env

        # Ensure the env var is NOT set before the call
        monkeypatch.delenv("AGENTIC_DEVTOOLS_STATE_DIR", raising=False)
        _start_copilot_session_for_pr_review(str(tmp_path))

        expected_state_dir = str(tmp_path / "scripts" / "temp")
        assert captured_state_dir == [expected_state_dir]
        # Env var must be restored (removed) after the call
        assert "AGENTIC_DEVTOOLS_STATE_DIR" not in os.environ

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_restores_pre_existing_state_dir_env_after_session(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Test that a pre-existing AGENTIC_DEVTOOLS_STATE_DIR is restored after the session."""
        import os

        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        # Set a pre-existing value
        original_state_dir = "/original/state/dir"
        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", original_state_dir)

        _start_copilot_session_for_pr_review(str(tmp_path))

        # The original value must be restored after the call
        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == original_state_dir

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
        """Test that the session is non-interactive when no TTY is attached (background task scenario)."""
        from unittest.mock import MagicMock

        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True  # VS Code available, but no TTY

        # Simulate no TTY (stdin/stdout are pipes, as in run_function_in_background)
        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # Must be non-interactive despite interactive=True and VS Code available
        mock_copilot.assert_called_once_with(
            prompt=COPILOT_SESSION_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_forces_non_interactive_when_stdout_has_no_isatty(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """Test that the session is non-interactive when stdout has no isatty (LogWriter background task scenario)."""

        class _NoIsattyWriter:
            """Simulates LogWriter from run_function_in_background - no isatty attribute."""

            def write(self, text: str) -> None:
                pass

            def flush(self) -> None:
                pass

        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Review prompt", encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True  # VS Code available, but stdout is a LogWriter

        monkeypatch.setattr("sys.stdout", _NoIsattyWriter())

        # Must not raise AttributeError for missing isatty
        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # Must be non-interactive because stdout is not a TTY
        mock_copilot.assert_called_once_with(
            prompt=COPILOT_SESSION_START_PROMPT,
            working_directory=str(tmp_path),
            interactive=False,
        )

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_skips_copilot_session_when_auto_start_task_present_and_no_tty(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When auto-start task exists in tasks.json, sentinel appears, and no TTY, skip start_copilot_session."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write a tasks.json with the auto-start task already present
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        # Create the sentinel file so the wait loop confirms the task ran
        sentinel_dir = tmp_path / ".agdt"
        sentinel_dir.mkdir(parents=True)
        (sentinel_dir / ".copilot-auto-start-triggered").write_text("", encoding="utf-8")

        mock_wait.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        # interactive=True is required for the auto-start detection path
        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        mock_copilot.assert_not_called()
        # stdout is a MagicMock, so check print() output via write calls
        written = "".join(call.args[0] for call in mock_stdout.write.call_args_list if call.args)
        assert "auto-start task confirmed running" in written

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_falls_through_when_auto_start_task_present_but_sentinel_never_appears(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When auto-start task present but sentinel never appears, fall through to background session."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write a tasks.json with the auto-start task
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        # Do NOT create the sentinel file — simulates VS Code not running the task

        mock_wait.return_value = True
        mock_vscode.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        # Mock time.sleep to avoid actual delay in tests
        with patch("time.sleep"):
            _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # Should fall through after the sentinel wait timeout
        mock_copilot.assert_called_once()
        written = "".join(call.args[0] for call in mock_stdout.write.call_args_list if call.args)
        assert "did not fire within" in written

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_falls_through_when_no_auto_start_task_in_tasks_json(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When tasks.json exists but has no auto-start task, fall through to start_copilot_session."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write a tasks.json without the auto-start task
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": "build", "type": "shell", "command": "make"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # Should fall through since there's no matching auto-start task
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_falls_through_when_tty_available_even_with_auto_start_task(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When TTY is available, fall through to start_copilot_session even if auto-start task exists."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write a tasks.json with the auto-start task
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = True
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = True
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available", return_value=False)
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_prints_fallback_notice_when_vscode_unavailable(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When VS Code is not available and no TTY, print fallback notice."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        mock_wait.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        # interactive=True required for fallback notice check
        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # stdout is a MagicMock, so check print() output via write calls
        written = "".join(call.args[0] for call in mock_stdout.write.call_args_list if call.args)
        assert "VS Code integrated terminal auto-start not available" in written
        assert "agdt-task-log" in written

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_vscode_available")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_does_not_check_auto_start_when_non_interactive(
        self,
        mock_wait,
        mock_vscode,
        mock_copilot,
        tmp_path,
    ):
        """Non-interactive mode (pipeline) should never check for auto-start task."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write a tasks.json with the auto-start task — should be ignored
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_data = {
            "version": "2.0.0",
            "tasks": [{"label": _AUTO_START_TASK_LABEL, "type": "shell", "command": "copilot"}],
        }
        (vscode_dir / "tasks.json").write_text(json.dumps(tasks_data), encoding="utf-8")

        mock_wait.return_value = True
        mock_vscode.return_value = True

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=False)

        # Should always start copilot session in non-interactive mode
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_falls_through_when_tasks_json_malformed(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When tasks.json is malformed JSON, fall through gracefully to start_copilot_session."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write malformed tasks.json
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text("not json", encoding="utf-8")

        mock_wait.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # Should fall through since JSON is malformed
        mock_copilot.assert_called_once()

    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch("agentic_devtools.cli.workflows.worktree_setup._wait_for_prompt_file")
    def test_falls_through_when_tasks_null_in_tasks_json(
        self,
        mock_wait,
        mock_copilot,
        tmp_path,
        monkeypatch,
    ):
        """When tasks.json has `tasks: null`, fall through gracefully (no TypeError)."""
        prompt_dir = tmp_path / "scripts" / "temp"
        prompt_dir.mkdir(parents=True)
        prompt_file = prompt_dir / "temp-pull-request-review-initiate-prompt.md"
        prompt_file.write_text("# Prompt", encoding="utf-8")

        # Write tasks.json with tasks: null
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "tasks.json").write_text(
            json.dumps({"version": "2.0.0", "tasks": None}),
            encoding="utf-8",
        )

        mock_wait.return_value = True

        mock_stdin = MagicMock()
        mock_stdin.isatty.return_value = False
        mock_stdout = MagicMock()
        mock_stdout.isatty.return_value = False
        monkeypatch.setattr("sys.stdin", mock_stdin)
        monkeypatch.setattr("sys.stdout", mock_stdout)

        _start_copilot_session_for_pr_review(str(tmp_path), interactive=True)

        # Should fall through since tasks is null (not a list with the auto-start task)
        mock_copilot.assert_called_once()


class TestCopilotSessionStartPrompt:
    """Tests for the COPILOT_SESSION_START_PROMPT constant."""

    def test_prompt_is_single_line(self):
        """The session start prompt must have no newline characters."""
        assert "\n" not in COPILOT_SESSION_START_PROMPT

    def test_prompt_instructs_advance_to_pull_request_overview(self):
        """The prompt must instruct the agent to run agdt-advance-workflow pull-request-overview."""
        assert "agdt-advance-workflow pull-request-overview" in COPILOT_SESSION_START_PROMPT

    def test_prompt_does_not_contain_template_variables(self):
        """The prompt must be a static string with no template variables."""
        assert "{{" not in COPILOT_SESSION_START_PROMPT
        assert "}}" not in COPILOT_SESSION_START_PROMPT
