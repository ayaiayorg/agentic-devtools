"""Tests for copilot_auto_start_cmd."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.copilot.auto_start import _cleanup_auto_start_task, copilot_auto_start_cmd

_AVAIL = "agentic_devtools.cli.copilot.auto_start.is_gh_copilot_available"
_BUILD = "agentic_devtools.cli.copilot.auto_start.build_copilot_args"
_SUBPROC = "agentic_devtools.cli.copilot.auto_start.subprocess.run"
_CLEANUP = "agentic_devtools.cli.copilot.auto_start._cleanup_auto_start_task"
_REMOVE = "agentic_devtools.cli.copilot.auto_start.remove_auto_start_task"
_WHICH = "agentic_devtools.cli.copilot.auto_start.shutil.which"
_GET_STATE_FILE = "agentic_devtools.cli.copilot.auto_start.get_state_file_path"

_RUN_ID = "test-run-123"


def _state_file(tmp_path: Path, triggered_runs: list | None = None) -> Path:
    """Create a state file with optional triggered runs and return its path."""
    state_dir = tmp_path / ".agdt" / "workflows" / "_test" / "_test"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "state.json"
    state: dict = {}
    if triggered_runs is not None:
        state["copilot"] = {"auto_start_triggered_runs": triggered_runs}
    state_file.write_text(json.dumps(state), encoding="utf-8")
    return state_file


def _read_triggered_runs(state_file: Path) -> list:
    """Read copilot.auto_start_triggered_runs from the state file."""
    content = state_file.read_text(encoding="utf-8")
    state = json.loads(content) if content.strip() else {}
    return state.get("copilot", {}).get("auto_start_triggered_runs", [])


class TestCopilotAutoStartCmd:
    """Tests for the copilot_auto_start_cmd entry point."""

    @pytest.fixture(autouse=True)
    def mock_agdt_which(self):
        """Patch shutil.which so agdt-advance-workflow appears on PATH by default."""
        with patch(_WHICH, return_value="/usr/local/bin/agdt-advance-workflow"):
            yield

    # ------------------------------------------------------------------
    # run_id validation
    # ------------------------------------------------------------------

    def test_exits_1_when_run_id_is_empty_or_whitespace(self, tmp_path, capsys):
        """Exits 1 when --run-id is empty or whitespace-only."""
        with pytest.raises(SystemExit) as exc_info:
            copilot_auto_start_cmd(
                [
                    "--worktree-path",
                    str(tmp_path),
                    "--start-prompt",
                    "hello",
                    "--run-id",
                    "   ",
                ]
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--run-id must be a non-empty, non-whitespace value" in captured.err

    # ------------------------------------------------------------------
    # Early worktree_path validation (before any filesystem writes)
    # ------------------------------------------------------------------

    def test_exits_1_when_worktree_path_does_not_exist(self, tmp_path, capsys):
        """Exits 1 with error message when --worktree-path does not exist."""
        nonexistent = str(tmp_path / "does_not_exist")
        with pytest.raises(SystemExit) as exc_info:
            copilot_auto_start_cmd(
                [
                    "--worktree-path",
                    nonexistent,
                    "--start-prompt",
                    "hello",
                    "--run-id",
                    _RUN_ID,
                ]
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist or is not a directory" in captured.err

    def test_exits_1_when_worktree_path_is_a_file(self, tmp_path, capsys):
        """Exits 1 with error message when --worktree-path points to a file, not a directory."""
        a_file = tmp_path / "some_file"
        a_file.write_text("", encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            copilot_auto_start_cmd(
                [
                    "--worktree-path",
                    str(a_file),
                    "--start-prompt",
                    "hello",
                    "--run-id",
                    _RUN_ID,
                ]
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not exist or is not a directory" in captured.err

    def test_no_filesystem_writes_when_worktree_path_invalid(self, tmp_path):
        """No directories or files are created when worktree_path is invalid."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(SystemExit):
            copilot_auto_start_cmd(
                [
                    "--worktree-path",
                    str(nonexistent),
                    "--start-prompt",
                    "hello",
                    "--run-id",
                    _RUN_ID,
                ]
            )

        # The nonexistent directory should NOT have been created
        assert not nonexistent.exists()

    # ------------------------------------------------------------------
    # State path resolution chdir/restore behavior
    # ------------------------------------------------------------------

    def test_exits_1_when_chdir_to_worktree_fails(self, tmp_path, capsys):
        """Exits 1 with a clear error when changing to worktree directory fails."""
        with patch("agentic_devtools.cli.copilot.auto_start.os.chdir", side_effect=OSError("denied")):
            with pytest.raises(SystemExit) as exc_info:
                copilot_auto_start_cmd(
                    [
                        "--worktree-path",
                        str(tmp_path),
                        "--start-prompt",
                        "hello",
                        "--run-id",
                        _RUN_ID,
                    ]
                )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "failed to change directory to worktree" in captured.err

    def test_warns_when_restoring_original_cwd_fails(self, tmp_path, capsys):
        """Prints a warning when restoring the original working directory fails."""
        sf = _state_file(tmp_path, triggered_runs=[_RUN_ID])

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch("agentic_devtools.cli.copilot.auto_start.os.chdir", side_effect=[None, OSError("restore failed")]):
                with patch(_CLEANUP):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(
                            [
                                "--worktree-path",
                                str(tmp_path),
                                "--start-prompt",
                                "hello",
                                "--run-id",
                                _RUN_ID,
                            ]
                        )

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "warning: failed to restore original working directory" in captured.err

    # ------------------------------------------------------------------
    # Run ID already triggered (exits before is_gh_copilot_available check)
    # ------------------------------------------------------------------

    def test_exits_0_when_run_id_already_triggered(self, tmp_path):
        """When the run ID is already in the triggered set, exit 0 immediately."""
        sf = _state_file(tmp_path, triggered_runs=[_RUN_ID])

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_REMOVE):
                with pytest.raises(SystemExit) as exc_info:
                    copilot_auto_start_cmd(
                        [
                            "--worktree-path",
                            str(tmp_path),
                            "--start-prompt",
                            "hello",
                            "--run-id",
                            _RUN_ID,
                        ]
                    )

        assert exc_info.value.code == 0

    def test_calls_remove_auto_start_task_when_run_id_already_triggered(self, tmp_path):
        """When run ID is already triggered, remove_auto_start_task is called for cleanup with delete_if_empty=False."""
        sf = _state_file(tmp_path, triggered_runs=[_RUN_ID])

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_REMOVE) as mock_remove:
                with pytest.raises(SystemExit):
                    copilot_auto_start_cmd(
                        [
                            "--worktree-path",
                            str(tmp_path),
                            "--start-prompt",
                            "hello",
                            "--run-id",
                            _RUN_ID,
                            "--task-label",
                            "my-label",
                        ]
                    )

        mock_remove.assert_called_once_with(str(tasks_path), str(vscode_dir), "my-label", delete_if_empty=False)

    def test_calls_remove_with_delete_if_empty_true_when_created_new_and_run_id_triggered(self, tmp_path):
        """When run ID is already triggered and --created-new is set, calls remove with delete_if_empty=True."""
        sf = _state_file(tmp_path, triggered_runs=[_RUN_ID])

        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_REMOVE) as mock_remove:
                with pytest.raises(SystemExit):
                    copilot_auto_start_cmd(
                        [
                            "--worktree-path",
                            str(tmp_path),
                            "--start-prompt",
                            "hello",
                            "--run-id",
                            _RUN_ID,
                            "--task-label",
                            "my-label",
                            "--created-new",
                        ]
                    )

        mock_remove.assert_called_once_with(str(tasks_path), str(vscode_dir), "my-label", delete_if_empty=True)

    def test_restores_state_env_vars_after_state_path_resolution(self, tmp_path, monkeypatch):
        """Both state-dir environment variables are restored after state-path resolution."""
        sf = _state_file(tmp_path, triggered_runs=[_RUN_ID])

        monkeypatch.setenv("AGENTIC_DEVTOOLS_STATE_DIR", "orig-modern")
        monkeypatch.setenv("DFLY_AI_HELPERS_STATE_DIR", "orig-legacy")

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_CLEANUP):
                with pytest.raises(SystemExit) as exc_info:
                    copilot_auto_start_cmd(
                        [
                            "--worktree-path",
                            str(tmp_path),
                            "--start-prompt",
                            "hello",
                            "--run-id",
                            _RUN_ID,
                        ]
                    )

        assert exc_info.value.code == 0
        assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == "orig-modern"
        assert os.environ.get("DFLY_AI_HELPERS_STATE_DIR") == "orig-legacy"

    # ------------------------------------------------------------------
    # Copilot CLI not available (new pre-flight check before marking)
    # ------------------------------------------------------------------

    def test_exits_1_when_copilot_not_available(self, tmp_path, capsys):
        """Exits 1 with error message when the copilot CLI is not available."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    copilot_auto_start_cmd(
                        [
                            "--worktree-path",
                            str(tmp_path),
                            "--start-prompt",
                            "hello",
                            "--run-id",
                            _RUN_ID,
                        ]
                    )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "copilot CLI not available" in captured.err

    def test_state_unchanged_when_copilot_not_available(self, tmp_path):
        """State is not modified when the copilot CLI is not available."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=False):
                with pytest.raises(SystemExit):
                    copilot_auto_start_cmd(
                        [
                            "--worktree-path",
                            str(tmp_path),
                            "--start-prompt",
                            "hello",
                            "--run-id",
                            _RUN_ID,
                        ]
                    )

        assert _RUN_ID not in _read_triggered_runs(sf)

    # ------------------------------------------------------------------
    # agdt-advance-workflow not on PATH (new pre-flight check 3b)
    # ------------------------------------------------------------------

    def test_exits_1_when_agdt_advance_workflow_not_on_path(self, tmp_path, capsys):
        """Exits 1 with error message when agdt-advance-workflow is not found on PATH."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_WHICH, return_value=None):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(
                            [
                                "--worktree-path",
                                str(tmp_path),
                                "--start-prompt",
                                "hello",
                                "--run-id",
                                _RUN_ID,
                            ]
                        )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "agdt-advance-workflow" in captured.err
        assert "not found on PATH" in captured.err

    def test_state_unchanged_when_agdt_advance_workflow_not_on_path(self, tmp_path):
        """State is not modified when agdt-advance-workflow is not found on PATH."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_WHICH, return_value=None):
                    with pytest.raises(SystemExit):
                        copilot_auto_start_cmd(
                            [
                                "--worktree-path",
                                str(tmp_path),
                                "--start-prompt",
                                "hello",
                                "--run-id",
                                _RUN_ID,
                            ]
                        )

        assert _RUN_ID not in _read_triggered_runs(sf)

    # ------------------------------------------------------------------
    # build_copilot_args returns None (CLI available but prompt too large)
    # ------------------------------------------------------------------

    def test_exits_1_when_build_copilot_args_returns_none(self, tmp_path, capsys):
        """When build_copilot_args returns None, print 'prompt too large' error and exit 1."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=None):
                    with pytest.raises(SystemExit) as exc_info:
                        copilot_auto_start_cmd(
                            [
                                "--worktree-path",
                                str(tmp_path),
                                "--start-prompt",
                                "hello",
                                "--run-id",
                                _RUN_ID,
                            ]
                        )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "start prompt is too large" in captured.err

    def test_state_unchanged_when_build_copilot_args_returns_none(self, tmp_path):
        """State is not modified when build_copilot_args returns None."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=None):
                    with pytest.raises(SystemExit):
                        copilot_auto_start_cmd(
                            [
                                "--worktree-path",
                                str(tmp_path),
                                "--start-prompt",
                                "hello",
                                "--run-id",
                                _RUN_ID,
                            ]
                        )

        assert _RUN_ID not in _read_triggered_runs(sf)

    # ------------------------------------------------------------------
    # Successful copilot run
    # ------------------------------------------------------------------

    def test_marks_run_triggered_before_running_copilot(self, tmp_path):
        """Run ID is marked in state before the copilot subprocess runs."""
        sf = _state_file(tmp_path)
        call_order = []

        def fake_build_args(prompt, interactive):
            return ["copilot", "-i", prompt]

        def fake_subprocess_run(args, **kwargs):
            # Run ID must already be marked when subprocess.run is called
            if _RUN_ID in _read_triggered_runs(sf):
                call_order.append("run_id_marked")
            call_order.append("subprocess_run")
            result = MagicMock()
            result.returncode = 0
            return result

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, side_effect=fake_build_args):
                    with patch(_SUBPROC, side_effect=fake_subprocess_run):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 0
        assert call_order == ["run_id_marked", "subprocess_run"]

    def test_exits_0_on_successful_copilot_run(self, tmp_path):
        """Exits 0 when the copilot command succeeds."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, return_value=mock_result):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 0

    def test_cleanup_called_on_success(self, tmp_path):
        """_cleanup_auto_start_task is called after a successful copilot run."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_GET_STATE_FILE, return_value=sf):
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
                                        "--run-id",
                                        _RUN_ID,
                                        "--task-label",
                                        "my-label",
                                        "--created-new",
                                    ]
                                )

        mock_cleanup.assert_called_once_with(str(tmp_path), "my-label", True)

    def test_run_id_remains_triggered_after_success(self, tmp_path):
        """Run ID remains in the triggered set after a successful copilot run."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, return_value=mock_result):
                        with patch(_CLEANUP):
                            with pytest.raises(SystemExit):
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert _RUN_ID in _read_triggered_runs(sf)

    def test_successfully_marks_run_id_when_existing_state_is_non_dict_json(self, tmp_path):
        """A valid non-object state.json is normalized before marking and running Copilot."""
        sf = _state_file(tmp_path)
        sf.write_text(json.dumps(["unexpected-top-level"]), encoding="utf-8")
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, return_value=mock_result):
                        with patch(_CLEANUP):
                            with pytest.raises(SystemExit) as exc_info:
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert exc_info.value.code == 0
        assert _read_triggered_runs(sf) == [_RUN_ID]

    # ------------------------------------------------------------------
    # Failed copilot run (non-zero exit code)
    # ------------------------------------------------------------------

    def test_exits_with_copilot_exit_code_on_failure(self, tmp_path):
        """Exits with the copilot command's non-zero exit code on failure."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 42

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, return_value=mock_result):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 42

    def test_run_id_unmarked_on_copilot_failure(self, tmp_path):
        """Run ID is removed from the triggered set when the copilot command fails."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, return_value=mock_result):
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert _RUN_ID not in _read_triggered_runs(sf)

    def test_cleanup_not_called_on_copilot_failure(self, tmp_path):
        """_cleanup_auto_start_task is NOT called when the copilot command fails."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch(_GET_STATE_FILE, return_value=sf):
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
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        mock_cleanup.assert_not_called()

    # ------------------------------------------------------------------
    # subprocess.run raises OSError (TOCTOU: binary removed from PATH)
    # ------------------------------------------------------------------

    def test_exits_1_when_subprocess_raises_oserror(self, tmp_path, capsys):
        """Exits 1 with error message when subprocess.run raises a generic OSError (e.g. cwd missing)."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=OSError("Permission denied")):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "failed to run Copilot CLI" in captured.err

    def test_run_id_unmarked_when_subprocess_raises_oserror(self, tmp_path):
        """Run ID is removed from the triggered set when subprocess.run raises OSError."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=OSError("No such file or directory")):
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert _RUN_ID not in _read_triggered_runs(sf)

    def test_cleanup_not_called_when_subprocess_raises_oserror(self, tmp_path):
        """_cleanup_auto_start_task is NOT called when subprocess.run raises OSError."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=OSError("No such file or directory")):
                        with patch(_CLEANUP) as mock_cleanup:
                            with pytest.raises(SystemExit):
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        mock_cleanup.assert_not_called()

    # ------------------------------------------------------------------
    # Marking failure (state file lock / OS error)
    # ------------------------------------------------------------------

    def test_exits_1_when_mark_run_triggered_raises_file_lock_error(self, tmp_path, capsys):
        """Exits 1 with error message when the state file lock cannot be acquired."""
        sf = _state_file(tmp_path)
        from agentic_devtools.file_locking import FileLockError

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start._mark_run_triggered",
                        side_effect=FileLockError("timeout"),
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "state file lock" in captured.err

    def test_exits_1_when_mark_run_triggered_raises_oserror(self, tmp_path, capsys):
        """Exits 1 with error message when state file cannot be updated."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start._mark_run_triggered",
                        side_effect=OSError("permission denied"),
                    ):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "state file" in captured.err

    def test_exits_0_when_run_id_already_marked_by_concurrent_invocation(self, tmp_path):
        """Exits 0 (without running Copilot) when _mark_run_triggered returns False (race)."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(
                        "agentic_devtools.cli.copilot.auto_start._mark_run_triggered",
                        return_value=False,
                    ):
                        with patch(_SUBPROC) as mock_subproc:
                            with pytest.raises(SystemExit) as exc_info:
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert exc_info.value.code == 0
        mock_subproc.assert_not_called()

    # ------------------------------------------------------------------
    # FileNotFoundError (binary not found) vs missing cwd (worktree removed)
    # ------------------------------------------------------------------

    def test_exits_1_with_binary_not_found_message_when_subprocess_raises_filenotfounderror(self, tmp_path, capsys):
        """Exits 1 with 'executable not found' message when the Copilot binary is missing from PATH."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=FileNotFoundError("gh: not found")):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "executable not found" in captured.err

    def test_exits_1_with_missing_worktree_message_when_subprocess_raises_filenotfounderror_for_cwd(
        self, tmp_path, capsys
    ):
        """Exits 1 with 'no longer exists' message when FileNotFoundError is due to missing cwd."""
        sf = _state_file(tmp_path)
        import shutil

        worktree_path = tmp_path / "worktree"
        worktree_path.mkdir()

        def fake_subprocess_run(args, **kwargs):
            shutil.rmtree(str(worktree_path))
            raise FileNotFoundError("No such file or directory")

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=fake_subprocess_run):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(worktree_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "no longer exists" in captured.err

    def test_exits_1_with_worktree_context_when_subprocess_raises_oserror(self, tmp_path, capsys):
        """Exits 1 with worktree path in message when subprocess.run raises a generic OSError."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=OSError("Permission denied")):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert str(tmp_path) in captured.err

    # ------------------------------------------------------------------
    # Default task label
    # ------------------------------------------------------------------

    def test_default_task_label_is_agdt_copilot_auto_start(self, tmp_path):
        """The default --task-label is 'agdt-copilot-auto-start'."""
        sf = _state_file(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch(_GET_STATE_FILE, return_value=sf):
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
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        mock_cleanup.assert_called_once_with(str(tmp_path), "agdt-copilot-auto-start", False)

    # ------------------------------------------------------------------
    # Unmark is best-effort (100% coverage)
    # ------------------------------------------------------------------

    def test_exits_1_gracefully_when_unmark_called_after_subprocess_filenotfounderror(self, tmp_path, capsys):
        """Exits 1 and calls unmark after FileNotFoundError from subprocess."""
        sf = _state_file(tmp_path)
        _UNMARK = "agentic_devtools.cli.copilot.auto_start._unmark_run_triggered"

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=FileNotFoundError("gh: not found")):
                        with patch(_UNMARK) as mock_unmark:
                            with pytest.raises(SystemExit) as exc_info:
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert exc_info.value.code == 1
        mock_unmark.assert_called_once_with(sf, _RUN_ID)
        captured = capsys.readouterr()
        assert "executable not found" in captured.err

    def test_exits_1_gracefully_when_unmark_called_after_subprocess_oserror(self, tmp_path, capsys):
        """Exits 1 and calls unmark after OSError from subprocess."""
        sf = _state_file(tmp_path)
        _UNMARK = "agentic_devtools.cli.copilot.auto_start._unmark_run_triggered"

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=OSError("Permission denied")):
                        with patch(_UNMARK) as mock_unmark:
                            with pytest.raises(SystemExit) as exc_info:
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert exc_info.value.code == 1
        mock_unmark.assert_called_once_with(sf, _RUN_ID)
        captured = capsys.readouterr()
        assert "failed to run Copilot CLI" in captured.err

    def test_exits_with_code_gracefully_when_unmark_called_after_copilot_failure(self, tmp_path):
        """Exits with copilot's exit code and calls unmark after a non-zero run."""
        sf = _state_file(tmp_path)
        _UNMARK = "agentic_devtools.cli.copilot.auto_start._unmark_run_triggered"
        mock_result = MagicMock()
        mock_result.returncode = 5

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, return_value=mock_result):
                        with patch(_UNMARK) as mock_unmark:
                            with pytest.raises(SystemExit) as exc_info:
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert exc_info.value.code == 5
        mock_unmark.assert_called_once_with(sf, _RUN_ID)

    # ------------------------------------------------------------------
    # KeyboardInterrupt handling (Ctrl+C while Copilot is running)
    # ------------------------------------------------------------------

    def test_exits_130_when_subprocess_raises_keyboard_interrupt(self, tmp_path):
        """Exits 130 when the user interrupts the Copilot subprocess with Ctrl+C."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                        with pytest.raises(SystemExit) as exc_info:
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert exc_info.value.code == 130

    def test_run_id_unmarked_when_subprocess_raises_keyboard_interrupt(self, tmp_path):
        """Run ID is removed from the triggered set when the user interrupts the Copilot subprocess."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                        with pytest.raises(SystemExit):
                            copilot_auto_start_cmd(
                                [
                                    "--worktree-path",
                                    str(tmp_path),
                                    "--start-prompt",
                                    "hello",
                                    "--run-id",
                                    _RUN_ID,
                                ]
                            )

        assert _RUN_ID not in _read_triggered_runs(sf)

    def test_cleanup_not_called_when_subprocess_raises_keyboard_interrupt(self, tmp_path):
        """_cleanup_auto_start_task is NOT called when the user interrupts the Copilot subprocess."""
        sf = _state_file(tmp_path)

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                        with patch(_CLEANUP) as mock_cleanup:
                            with pytest.raises(SystemExit):
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        mock_cleanup.assert_not_called()

    def test_exits_130_gracefully_when_unmark_called_after_keyboard_interrupt(self, tmp_path):
        """Exits 130 and calls unmark after KeyboardInterrupt."""
        sf = _state_file(tmp_path)
        _UNMARK = "agentic_devtools.cli.copilot.auto_start._unmark_run_triggered"

        with patch(_GET_STATE_FILE, return_value=sf):
            with patch(_AVAIL, return_value=True):
                with patch(_BUILD, return_value=["copilot", "-i", "hello"]):
                    with patch(_SUBPROC, side_effect=KeyboardInterrupt):
                        with patch(_UNMARK) as mock_unmark:
                            with pytest.raises(SystemExit) as exc_info:
                                copilot_auto_start_cmd(
                                    [
                                        "--worktree-path",
                                        str(tmp_path),
                                        "--start-prompt",
                                        "hello",
                                        "--run-id",
                                        _RUN_ID,
                                    ]
                                )

        assert exc_info.value.code == 130
        mock_unmark.assert_called_once_with(sf, _RUN_ID)


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
