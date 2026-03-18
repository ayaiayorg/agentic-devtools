"""Tests for copilot_auto_start_cmd."""

import json
import shutil
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.copilot.auto_start import _cleanup_auto_start_task, copilot_auto_start_cmd

_AVAIL = "agentic_devtools.cli.copilot.auto_start.is_gh_copilot_available"
_BUILD = "agentic_devtools.cli.copilot.auto_start.build_copilot_args"
_SUBPROC = "agentic_devtools.cli.copilot.auto_start.subprocess.run"
_CLEANUP = "agentic_devtools.cli.copilot.auto_start._cleanup_auto_start_task"
_REMOVE = "agentic_devtools.cli.copilot.auto_start.remove_auto_start_task"


class TestCopilotAutoStartCmd:
    """Tests for the copilot_auto_start_cmd entry point."""

    # ------------------------------------------------------------------
    # Early worktree_path validation (before any filesystem writes)
    # ------------------------------------------------------------------

    def test_exits_1_when_worktree_path_does_not_exist(self, tmp_path, capsys):
        """Exits 1 with error message when --worktree-path does not exist."""
        nonexistent = str(tmp_path / "does_not_exist")
        with pytest.raises(SystemExit) as exc_info:
            copilot_auto_start_cmd(["--worktree-path", nonexistent, "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist or is not a directory" in captured.err

    def test_exits_1_when_worktree_path_is_a_file(self, tmp_path, capsys):
        """Exits 1 with error message when --worktree-path points to a file, not a directory."""
        a_file = tmp_path / "some_file"
        a_file.write_text("", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            copilot_auto_start_cmd(["--worktree-path", str(a_file), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist or is not a directory" in captured.err

    def test_no_filesystem_writes_when_worktree_path_invalid(self, tmp_path):
        """No directories or files are created when worktree_path is invalid."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(SystemExit):
            copilot_auto_start_cmd(["--worktree-path", str(nonexistent), "--start-prompt", "hello"])

        # The nonexistent directory should NOT have been created
        assert not nonexistent.exists()

    # ------------------------------------------------------------------
    # Sentinel-already-exists path (exits before is_gh_copilot_available check)
    # ------------------------------------------------------------------

    def test_exits_0_when_sentinel_already_exists(self, tmp_path):
        """When the sentinel file already exists, exit 0 immediately."""
        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        with patch(_REMOVE):
            with pytest.raises(SystemExit) as exc_info:
                copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 0

    def test_calls_remove_auto_start_task_when_sentinel_exists(self, tmp_path):
        """When sentinel exists, remove_auto_start_task is called for cleanup with delete_if_empty=False."""
        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"

        with patch(_REMOVE) as mock_remove:
            with pytest.raises(SystemExit):
                copilot_auto_start_cmd(
                    ["--worktree-path", str(tmp_path), "--start-prompt", "hello", "--task-label", "my-label"]
                )

        mock_remove.assert_called_once_with(str(tasks_path), str(vscode_dir), "my-label", delete_if_empty=False)

    def test_calls_remove_with_delete_if_empty_true_when_created_new_and_sentinel_exists(self, tmp_path):
        """When sentinel exists and --created-new is set, calls remove with delete_if_empty=True."""
        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("", encoding="utf-8")

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"

        with patch(_REMOVE) as mock_remove:
            with pytest.raises(SystemExit):
                copilot_auto_start_cmd(
                    [
                        "--worktree-path",
                        str(tmp_path),
                        "--start-prompt",
                        "hello",
                        "--task-label",
                        "my-label",
                        "--created-new",
                    ]
                )

        mock_remove.assert_called_once_with(str(tasks_path), str(vscode_dir), "my-label", delete_if_empty=True)

    # ------------------------------------------------------------------
    # Copilot CLI not available (new pre-flight check before sentinel creation)
    # ------------------------------------------------------------------

    def test_exits_1_when_copilot_not_available(self, tmp_path, capsys):
        """Exits 1 with error message when the copilot CLI is not available."""
        with patch(_AVAIL, return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "copilot CLI not available" in captured.err

    def test_no_sentinel_created_when_copilot_not_available(self, tmp_path):
        """Sentinel file is NOT created when the copilot CLI is not available."""
        with patch(_AVAIL, return_value=False):
            with pytest.raises(SystemExit):
                copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        assert not sentinel.exists()

    # ------------------------------------------------------------------
    # build_copilot_args returns None (CLI available but prompt too large)
    # ------------------------------------------------------------------

    def test_exits_1_when_build_copilot_args_returns_none(self, tmp_path, capsys):
        """When build_copilot_args returns None, print 'prompt too large' error and exit 1."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "start prompt is too large" in captured.err

    def test_no_sentinel_created_when_build_copilot_args_returns_none(self, tmp_path):
        """Sentinel file is NOT created when build_copilot_args returns None."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=None):
                with pytest.raises(SystemExit):
                    copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        assert not sentinel.exists()

    # ------------------------------------------------------------------
    # Successful copilot run
    # ------------------------------------------------------------------

    def test_creates_sentinel_before_running_copilot(self, tmp_path):
        """Sentinel file is created before the copilot subprocess runs."""
        call_order = []

        def fake_build_args(prompt, interactive):
            return ["copilot", "-i", prompt]

        def fake_subprocess_run(args, **kwargs):
            # Sentinel must already exist when subprocess.run is called
            sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
            if sentinel.exists():
                call_order.append("sentinel_exists")
            call_order.append("subprocess_run")
            result = MagicMock()
            result.returncode = 0
            return result

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, side_effect=fake_build_args):
                with patch(_SUBPROC, side_effect=fake_subprocess_run):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 0
        assert call_order == ["sentinel_exists", "subprocess_run"]

    def test_exits_0_on_successful_copilot_run(self, tmp_path):
        """Exits 0 when the copilot command succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 0

    def test_cleanup_called_on_success(self, tmp_path):
        """_cleanup_auto_start_task is called after a successful copilot run."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with patch(_CLEANUP) as mock_cleanup:
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--task-label",
                                    "my-label",
                                    "--created-new",
                                ]
                            )

        mock_cleanup.assert_called_once_with(str(tmp_path), "my-label", True)

    def test_sentinel_remains_after_success(self, tmp_path):
        """Sentinel file is kept after a successful copilot run."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with patch(_CLEANUP):
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        assert sentinel.exists()

    # ------------------------------------------------------------------
    # Failed copilot run (non-zero exit code)
    # ------------------------------------------------------------------

    def test_exits_with_copilot_exit_code_on_failure(self, tmp_path):
        """Exits with the copilot command's non-zero exit code on failure."""
        mock_result = MagicMock()
        mock_result.returncode = 42

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 42

    def test_sentinel_removed_on_copilot_failure(self, tmp_path):
        """Sentinel file is removed when the copilot command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with pytest.raises(SystemExit):
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        assert not sentinel.exists()

    def test_cleanup_not_called_on_copilot_failure(self, tmp_path):
        """_cleanup_auto_start_task is NOT called when the copilot command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with patch(_CLEANUP) as mock_cleanup:
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        mock_cleanup.assert_not_called()

    # ------------------------------------------------------------------
    # subprocess.run raises OSError (TOCTOU: binary removed from PATH)
    # ------------------------------------------------------------------

    def test_exits_1_when_subprocess_raises_oserror(self, tmp_path, capsys):
        """Exits 1 with error message when subprocess.run raises a generic OSError (e.g. cwd missing)."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=OSError("Permission denied")):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "failed to run Copilot CLI" in captured.err

    def test_sentinel_removed_when_subprocess_raises_oserror(self, tmp_path):
        """Sentinel file is removed when subprocess.run raises OSError."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=OSError("No such file or directory")):
                    with pytest.raises(SystemExit):
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        assert not sentinel.exists()

    def test_cleanup_not_called_when_subprocess_raises_oserror(self, tmp_path):
        """_cleanup_auto_start_task is NOT called when subprocess.run raises OSError."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=OSError("No such file or directory")):
                    with patch(_CLEANUP) as mock_cleanup:
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        mock_cleanup.assert_not_called()

    # ------------------------------------------------------------------
    # Sentinel creation failure
    # ------------------------------------------------------------------

    def test_exits_1_when_sentinel_creation_fails(self, tmp_path, capsys):
        """Exits 1 with error message when sentinel file cannot be created."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(
                    "agentic_devtools.cli.copilot.auto_start.os.makedirs",
                    side_effect=OSError("permission denied"),
                ):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "sentinel" in captured.err

    def test_exits_0_when_sentinel_already_created_by_concurrent_invocation(self, tmp_path):
        """Exits 0 (without running Copilot) when atomic sentinel creation raises FileExistsError."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(
                    "agentic_devtools.cli.copilot.auto_start.os.open",
                    side_effect=FileExistsError("already exists"),
                ):
                    with patch(_SUBPROC) as mock_subproc:
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 0
        mock_subproc.assert_not_called()

    # ------------------------------------------------------------------
    # FileNotFoundError (binary not found) vs missing cwd (worktree removed)
    # ------------------------------------------------------------------

    def test_exits_1_with_binary_not_found_message_when_subprocess_raises_filenotfounderror(self, tmp_path, capsys):
        """Exits 1 with 'executable not found' message when the Copilot binary is missing from PATH."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=FileNotFoundError("gh: not found")):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "executable not found" in captured.err

    def test_exits_1_with_missing_worktree_message_when_subprocess_raises_filenotfounderror_for_cwd(
        self, tmp_path, capsys
    ):
        """Exits 1 with 'no longer exists' message when FileNotFoundError is due to missing cwd."""
        # Simulate the worktree being removed between sentinel creation and subprocess.run()
        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        def fake_subprocess_run(args, **kwargs):
            # Delete the worktree to simulate removal after sentinel creation
            shutil.rmtree(str(worktree_path))
            raise FileNotFoundError("No such file or directory")

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=fake_subprocess_run):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(worktree_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "no longer exists" in captured.err

    def test_exits_1_with_worktree_context_when_subprocess_raises_oserror(self, tmp_path, capsys):
        """Exits 1 with worktree path in message when subprocess.run raises a generic OSError."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=OSError("Permission denied")):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        # Message should mention the worktree path so user can diagnose cwd issues
        assert str(tmp_path) in captured.err

    # ------------------------------------------------------------------
    # Default task label
    # ------------------------------------------------------------------

    def test_default_task_label_is_agdt_copilot_auto_start(self, tmp_path):
        """The default --task-label is 'agdt-copilot-auto-start'."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with patch(_CLEANUP) as mock_cleanup:
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        # Default label is used
        mock_cleanup.assert_called_once_with(str(tmp_path), "agdt-copilot-auto-start", False)

    # ------------------------------------------------------------------
    # Sentinel removal failure (best-effort OSError guards, 100% coverage)
    # ------------------------------------------------------------------

    def test_exits_1_gracefully_when_sentinel_removal_fails_after_subprocess_filenotfounderror(self, tmp_path, capsys):
        """Exits 1 even when sentinel removal fails inside the FileNotFoundError handler."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=FileNotFoundError("gh: not found")):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start.os.remove",
                        side_effect=OSError("sentinel already gone"),
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "executable not found" in captured.err

    def test_exits_1_gracefully_when_sentinel_removal_fails_after_subprocess_oserror(self, tmp_path, capsys):
        """Exits 1 even when sentinel removal fails inside the subprocess OSError handler."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=OSError("Permission denied")):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start.os.remove",
                        side_effect=OSError("sentinel already gone"),
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "failed to run Copilot CLI" in captured.err

    def test_exits_with_code_gracefully_when_sentinel_removal_fails_after_copilot_failure(self, tmp_path):
        """Exits with copilot's exit code even when sentinel removal fails after a non-zero run."""
        mock_result = MagicMock()
        mock_result.returncode = 5

        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, return_value=mock_result):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start.os.remove",
                        side_effect=OSError("sentinel already gone"),
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 5

    # ------------------------------------------------------------------
    # KeyboardInterrupt handling (Ctrl+C while Copilot is running)
    # ------------------------------------------------------------------

    def test_exits_130_when_subprocess_raises_keyboard_interrupt(self, tmp_path):
        """Exits 130 when the user interrupts the Copilot subprocess with Ctrl+C."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 130

    def test_sentinel_removed_when_subprocess_raises_keyboard_interrupt(self, tmp_path):
        """Sentinel file is removed when the user interrupts the Copilot subprocess."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                    with pytest.raises(SystemExit):
                        copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        sentinel = tmp_path / ".agdt" / ".copilot-auto-start-triggered"
        assert not sentinel.exists()

    def test_cleanup_not_called_when_subprocess_raises_keyboard_interrupt(self, tmp_path):
        """_cleanup_auto_start_task is NOT called when the user interrupts the Copilot subprocess."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                    with patch(_CLEANUP) as mock_cleanup:
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        mock_cleanup.assert_not_called()

    def test_exits_130_gracefully_when_sentinel_removal_fails_after_keyboard_interrupt(self, tmp_path):
        """Exits 130 even when sentinel removal fails after KeyboardInterrupt."""
        with patch(_AVAIL, return_value=True):
            with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start.os.remove",
                        side_effect=OSError("sentinel already gone"),
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(["--worktree-path", str(tmp_path), "--start-prompt", "hello"])

        assert exc_info.value.code == 130


class TestCleanupAutoStartTask:
    """Tests for the _cleanup_auto_start_task helper."""

    # ------------------------------------------------------------------
    # File doesn't exist
    # ------------------------------------------------------------------

    def test_noop_when_tasks_json_absent(self, tmp_path):
        """Does nothing when tasks.json doesn't exist (no error)."""
        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=True)
        # No exception raised

    # ------------------------------------------------------------------
    # Tasks remain after removal
    # ------------------------------------------------------------------

    def test_rewrites_file_when_other_tasks_remain(self, tmp_path):
        """Rewrites tasks.json when other tasks remain after removing the target."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [
                {"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"},
                {"label": "user-task", "type": "shell", "command": "echo hi"},
            ],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["label"] == "user-task"
        assert vscode_dir.exists()

    # ------------------------------------------------------------------
    # No tasks remain, created_new=True
    # ------------------------------------------------------------------

    def test_deletes_file_when_created_new_and_no_tasks_remain(self, tmp_path):
        """Deletes tasks.json when created_new=True and no tasks remain."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=True)

        assert not tasks_path.exists()

    def test_removes_vscode_dir_when_empty_after_file_deletion(self, tmp_path):
        """Removes .vscode/ when it is empty after tasks.json deletion."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=True)

        assert not vscode_dir.exists()

    def test_keeps_vscode_dir_when_not_empty_after_file_deletion(self, tmp_path):
        """Keeps .vscode/ when other files remain after tasks.json deletion."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=True)

        assert not tasks_path.exists()
        assert vscode_dir.exists()

    def test_rewrites_with_empty_tasks_when_created_new_and_extra_keys(self, tmp_path):
        """Rewrites with empty tasks (not deletes) when created_new=True but extra keys are present."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"}],
            "inputs": [{"id": "myInput", "type": "promptString"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=True)

        # File must still exist and preserve the extra key
        assert tasks_path.exists()
        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []
        assert result["inputs"] == [{"id": "myInput", "type": "promptString"}]

    # ------------------------------------------------------------------
    # No tasks remain, created_new=False
    # ------------------------------------------------------------------

    def test_rewrites_with_empty_tasks_when_not_created_new_no_extra_keys(self, tmp_path):
        """Rewrites file with empty tasks array when pre-existing and no extra keys."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []
        assert tasks_path.exists()

    def test_preserves_extra_keys_when_not_created_new(self, tmp_path):
        """Preserves extra top-level keys (e.g. inputs) when rewriting."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"}],
            "inputs": [{"id": "myInput", "type": "promptString"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []
        assert result["inputs"] == [{"id": "myInput", "type": "promptString"}]

    # ------------------------------------------------------------------
    # Task not present — noop
    # ------------------------------------------------------------------

    def test_noop_when_task_not_present(self, tmp_path):
        """Does nothing when the target task is not in tasks.json."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "user-task", "type": "shell", "command": "echo hi"}],
        }
        original = json.dumps(data)
        tasks_path.write_text(original, encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        # File content is unchanged
        assert tasks_path.read_text(encoding="utf-8") == original

    # ------------------------------------------------------------------
    # Non-dict items in tasks array preserved
    # ------------------------------------------------------------------

    def test_preserves_non_dict_items_in_tasks(self, tmp_path):
        """Non-dict items in the tasks array are preserved during cleanup."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [
                "a string task",
                42,
                {"label": "agdt-copilot-auto-start", "type": "shell", "command": "cmd"},
            ],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert "a string task" in result["tasks"]
        assert 42 in result["tasks"]
        assert not any(isinstance(t, dict) and t.get("label") == "agdt-copilot-auto-start" for t in result["tasks"])

    # ------------------------------------------------------------------
    # Error handling — silently caught
    # ------------------------------------------------------------------

    def test_silently_ignores_malformed_json(self, tmp_path):
        """Silently ignores malformed JSON in tasks.json."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text("{invalid json", encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        # File is untouched, no exception
        assert tasks_path.read_text(encoding="utf-8") == "{invalid json"

    def test_silently_ignores_os_error_on_read(self, tmp_path):
        """Silently ignores OSError when reading tasks.json."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text("{}", encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("permission denied")):
            _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)
        # No exception raised

    def test_silently_ignores_non_dict_top_level(self, tmp_path):
        """Silently ignores tasks.json with a non-dict top-level value."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text("[1, 2, 3]", encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        assert tasks_path.read_text(encoding="utf-8") == "[1, 2, 3]"

    def test_silently_ignores_non_list_tasks_value(self, tmp_path):
        """Silently ignores tasks.json when tasks value is not a list."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text('{"version": "2.0.0", "tasks": null}', encoding="utf-8")

        _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)

        # File is unchanged
        assert "null" in tasks_path.read_text(encoding="utf-8")

    def test_silently_ignores_exception_from_remove_auto_start_task(self, tmp_path):
        """Silently ignores any exception raised directly by remove_auto_start_task."""
        with patch(_REMOVE, side_effect=RuntimeError("unexpected failure")):
            # Must not raise despite remove_auto_start_task raising
            _cleanup_auto_start_task(str(tmp_path), "agdt-copilot-auto-start", created_new=False)
