"""Tests for retry_autostart_cmd."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.copilot.auto_start import retry_autostart_cmd

_MODULE = "agentic_devtools.cli.copilot.auto_start"
_RESOLVE = "agentic_devtools.cli.workflows.worktree_setup._resolve_state_context_in_worktree"
_UNMARK = f"{_MODULE}._unmark_run_triggered"
_AUTO_START = f"{_MODULE}.copilot_auto_start_cmd"

_RUN_ID = "test-run-abc"
_PROMPT = "Hello, start working on the task."


def _write_marker(
    tmp_path: Path,
    *,
    run_id: str = _RUN_ID,
    start_prompt: str = _PROMPT,
    model: str | None = None,
    worktree_path: str | None = None,
    extra: dict | None = None,
) -> Path:
    """Write a pending auto-start marker and return the marker file path."""
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    marker: dict = {
        "run_id": run_id,
        "start_prompt": start_prompt,
        "model": model,
        "worktree_path": worktree_path or str(tmp_path),
        "created_utc": "2024-01-01T00:00:00+00:00",
        "task_label": "agdt-copilot-auto-start",
    }
    if extra:
        marker.update(extra)
    marker_path = vscode_dir / "pending-auto-start.json"
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    return marker_path


class TestRetryAutostartCmd:
    """Tests for the retry_autostart_cmd entry point."""

    # ------------------------------------------------------------------
    # Marker file missing
    # ------------------------------------------------------------------

    def test_exits_1_when_marker_missing(self, tmp_path, capsys):
        """Exits 1 with error message when marker file does not exist."""
        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "no pending auto-start marker found" in err

    # ------------------------------------------------------------------
    # Marker file is not valid JSON
    # ------------------------------------------------------------------

    def test_exits_1_when_marker_invalid_json(self, tmp_path, capsys):
        """Exits 1 with error message when marker file is corrupt."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "pending-auto-start.json").write_text("not valid json {{{", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "could not parse pending auto-start marker" in err

    # ------------------------------------------------------------------
    # Marker is not a dict
    # ------------------------------------------------------------------

    def test_exits_1_when_marker_is_not_dict(self, tmp_path, capsys):
        """Exits 1 when marker is a JSON array instead of object."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "pending-auto-start.json").write_text('["not", "a", "dict"]', encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "invalid format (expected JSON object)" in err

    # ------------------------------------------------------------------
    # Missing required fields
    # ------------------------------------------------------------------

    def test_exits_1_when_run_id_missing(self, tmp_path, capsys):
        """Exits 1 when marker has no run_id field."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "pending-auto-start.json").write_text(json.dumps({"start_prompt": "hello"}), encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "missing required field 'run_id'" in err

    def test_exits_1_when_start_prompt_missing(self, tmp_path, capsys):
        """Exits 1 when marker has no start_prompt field."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "pending-auto-start.json").write_text(json.dumps({"run_id": "run-1"}), encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "missing required field 'start_prompt'" in err

    def test_exits_1_when_run_id_is_empty_string(self, tmp_path, capsys):
        """Exits 1 when run_id is an empty string."""
        _write_marker(tmp_path, run_id="")

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "missing required field 'run_id'" in err

    def test_exits_1_when_start_prompt_is_whitespace(self, tmp_path, capsys):
        """Exits 1 when start_prompt is whitespace-only."""
        _write_marker(tmp_path, start_prompt="   ")

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "missing required field 'start_prompt'" in err

    def test_exits_1_when_run_id_is_not_string(self, tmp_path, capsys):
        """Exits 1 when run_id is an integer instead of string."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / "pending-auto-start.json").write_text(
            json.dumps({"run_id": 42, "start_prompt": "hello", "worktree_path": str(tmp_path)}),
            encoding="utf-8",
        )

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "missing required field 'run_id'" in err

    # ------------------------------------------------------------------
    # Worktree path validation
    # ------------------------------------------------------------------

    def test_exits_1_when_marker_worktree_path_nonexistent(self, tmp_path, capsys, monkeypatch):
        """Exits 1 when the marker's worktree_path references a non-existent directory."""
        _write_marker(tmp_path, worktree_path="/nonexistent/path/xyz")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd([])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "worktree path does not exist" in err

    def test_exits_1_when_marker_worktree_path_is_non_string(self, tmp_path, capsys, monkeypatch):
        """Exits 1 when marker's worktree_path is a non-string type (e.g., list)."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        marker = {
            "run_id": _RUN_ID,
            "start_prompt": _PROMPT,
            "worktree_path": ["/some/path"],
        }
        (vscode_dir / "pending-auto-start.json").write_text(json.dumps(marker), encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(SystemExit) as exc_info:
            retry_autostart_cmd([])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "worktree path does not exist" in err

    # ------------------------------------------------------------------
    # Stale-marker check
    # ------------------------------------------------------------------

    def test_exits_1_on_stale_marker_without_force(self, tmp_path, capsys):
        """Exits 1 when marker run_id does not match state run_id and --force not set."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, "different-run-id")):
            with pytest.raises(SystemExit) as exc_info:
                retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert f"marker run_id ({_RUN_ID})" in err
        assert "different-run-id" in err
        assert "--force" in err

    def test_stale_marker_proceeds_with_force(self, tmp_path):
        """Stale marker proceeds when --force is set."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, "different-run-id")):
            with patch(_UNMARK) as mock_unmark:
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path), "--force"])

        mock_unmark.assert_called_once_with(state_file, _RUN_ID)
        mock_auto.assert_called_once()

    def test_warns_when_state_unreadable_without_force(self, tmp_path, capsys):
        """When state is unreadable, warns and proceeds rather than blocking."""
        _write_marker(tmp_path)

        with patch(_RESOLVE, return_value=(None, "")):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        err = capsys.readouterr().err
        assert "could not read state" in err
        # Should still proceed — unmark not called because state_file_path is None
        mock_auto.assert_called_once()

    # ------------------------------------------------------------------
    # Happy path — valid marker
    # ------------------------------------------------------------------

    def test_valid_marker_delegates_to_copilot_auto_start(self, tmp_path):
        """Valid marker: calls _unmark_run_triggered then delegates to copilot_auto_start_cmd."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK) as mock_unmark:
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        mock_unmark.assert_called_once_with(state_file, _RUN_ID)
        mock_auto.assert_called_once()
        call_argv = mock_auto.call_args[1]["argv"]
        assert "--worktree-path" in call_argv
        assert "--start-prompt" in call_argv
        assert "--run-id" in call_argv
        assert _RUN_ID in call_argv
        assert _PROMPT in call_argv

    def test_model_included_in_delegated_argv_when_present(self, tmp_path):
        """When model is present in marker, --model is included in delegated argv."""
        _write_marker(tmp_path, model="gpt-4o")
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        call_argv = mock_auto.call_args[1]["argv"]
        assert "--model" in call_argv
        model_idx = call_argv.index("--model")
        assert call_argv[model_idx + 1] == "gpt-4o"

    def test_model_not_included_when_absent(self, tmp_path):
        """When model is None in marker, --model is not included in delegated argv."""
        _write_marker(tmp_path, model=None)
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        call_argv = mock_auto.call_args[1]["argv"]
        assert "--model" not in call_argv

    def test_model_not_included_when_empty_string(self, tmp_path):
        """When model is an empty string in marker, --model is not included."""
        _write_marker(tmp_path, model="")
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        call_argv = mock_auto.call_args[1]["argv"]
        assert "--model" not in call_argv

    # ------------------------------------------------------------------
    # --worktree-path overrides CWD for marker lookup
    # ------------------------------------------------------------------

    def test_worktree_path_arg_overrides_cwd(self, tmp_path):
        """--worktree-path argument controls where the marker is read from."""
        sub = tmp_path / "my-worktree"
        sub.mkdir()
        _write_marker(sub, worktree_path=str(sub))
        state_file = sub / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(sub)])

        call_argv = mock_auto.call_args[1]["argv"]
        wt_idx = call_argv.index("--worktree-path")
        assert call_argv[wt_idx + 1] == str(sub)

    def test_cli_worktree_path_overrides_marker_worktree_path(self, tmp_path):
        """CLI --worktree-path takes precedence over marker's worktree_path for delegation."""
        cli_wt = tmp_path / "cli-wt"
        cli_wt.mkdir()
        # Marker is written in cli_wt but marker's worktree_path points elsewhere
        marker_wt = tmp_path / "marker-wt"
        marker_wt.mkdir()
        _write_marker(cli_wt, worktree_path=str(marker_wt))
        state_file = cli_wt / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(cli_wt)])

        call_argv = mock_auto.call_args[1]["argv"]
        wt_idx = call_argv.index("--worktree-path")
        # CLI arg takes precedence
        assert call_argv[wt_idx + 1] == str(cli_wt)

    # ------------------------------------------------------------------
    # Defaults to CWD when --worktree-path omitted
    # ------------------------------------------------------------------

    def test_defaults_to_cwd_when_worktree_path_omitted(self, tmp_path, monkeypatch):
        """When --worktree-path is omitted, marker is read from CWD."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"
        monkeypatch.chdir(tmp_path)

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd([])

        mock_auto.assert_called_once()

    # ------------------------------------------------------------------
    # OSError reading marker file
    # ------------------------------------------------------------------

    def test_exits_1_on_marker_read_oserror(self, tmp_path, capsys):
        """Exits 1 when the marker file cannot be read due to OSError."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        marker_path = vscode_dir / "pending-auto-start.json"
        marker_path.write_text("{}", encoding="utf-8")

        with patch(f"{_MODULE}.open", side_effect=OSError("Permission denied")):
            with patch(f"{_MODULE}.os.path.isfile", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "could not read pending auto-start marker" in err

    # ------------------------------------------------------------------
    # Stale-marker check with matching run_id proceeds
    # ------------------------------------------------------------------

    def test_matching_run_id_proceeds(self, tmp_path):
        """When marker run_id matches state run_id, retry proceeds normally."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, _RUN_ID)):
            with patch(_UNMARK) as mock_unmark:
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        mock_unmark.assert_called_once()
        mock_auto.assert_called_once()

    # ------------------------------------------------------------------
    # Stale-marker check with empty state run_id proceeds
    # ------------------------------------------------------------------

    def test_empty_state_run_id_proceeds(self, tmp_path):
        """When state run_id is empty, stale check passes (no mismatch)."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"

        with patch(_RESOLVE, return_value=(state_file, "")):
            with patch(_UNMARK):
                with patch(_AUTO_START) as mock_auto:
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        mock_auto.assert_called_once()

    # ------------------------------------------------------------------
    # --force skips stale check entirely
    # ------------------------------------------------------------------

    def test_force_skips_resolve_for_stale_check(self, tmp_path):
        """--force does not call _resolve_state_context_in_worktree for stale check."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"

        # _resolve is called for the unmark step, but never for the stale check
        with patch(_RESOLVE, return_value=(state_file, "something-else")) as mock_resolve:
            with patch(_UNMARK):
                with patch(_AUTO_START):
                    retry_autostart_cmd(["--worktree-path", str(tmp_path), "--force"])

        # Called once for unmark resolution, but not for stale check
        assert mock_resolve.call_count == 1

    # ------------------------------------------------------------------
    # Unmark not called when state_file_path is None
    # ------------------------------------------------------------------

    def test_unmark_not_called_when_state_file_none(self, tmp_path):
        """_unmark_run_triggered is not called when state file path is None."""
        _write_marker(tmp_path)

        with patch(_RESOLVE, return_value=(None, "")):
            with patch(_UNMARK) as mock_unmark:
                with patch(_AUTO_START):
                    retry_autostart_cmd(["--worktree-path", str(tmp_path)])

        mock_unmark.assert_not_called()
