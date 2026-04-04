"""Tests for _try_terminal_send_fallback."""

import json
from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _PENDING_AUTO_START_FILENAME,
    _try_terminal_send_fallback,
)

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


def _write_marker(tmp_path, run_id="run-1", start_prompt="hello", model=None):
    """Write a pending auto-start marker file for testing."""
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    marker = {
        "run_id": run_id,
        "start_prompt": start_prompt,
        "model": model,
        "worktree_path": str(tmp_path),
        "created_utc": "2024-01-01T00:00:00+00:00",
        "task_label": "agdt-copilot-auto-start",
    }
    (vscode_dir / _PENDING_AUTO_START_FILENAME).write_text(json.dumps(marker), encoding="utf-8")


class TestTryTerminalSendFallback:
    """Tests for the _try_terminal_send_fallback helper."""

    def test_returns_false_in_test_environment(self, tmp_path):
        """Returns False immediately when running in a pytest environment."""
        _write_marker(tmp_path)
        # _in_test_environment() returns True by default during pytest runs
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_returns_false_when_no_marker_file(self, mock_env, tmp_path):
        """Returns False when no marker file exists."""
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_returns_false_on_invalid_json_marker(self, mock_env, tmp_path):
        """Returns False when marker file contains invalid JSON."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / _PENDING_AUTO_START_FILENAME).write_text("not json", encoding="utf-8")
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_returns_false_when_marker_missing_run_id(self, mock_env, tmp_path):
        """Returns False when marker file is missing run_id."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / _PENDING_AUTO_START_FILENAME).write_text(json.dumps({"start_prompt": "hello"}), encoding="utf-8")
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_returns_false_when_marker_missing_start_prompt(self, mock_env, tmp_path):
        """Returns False when marker file is missing start_prompt."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / _PENDING_AUTO_START_FILENAME).write_text(json.dumps({"run_id": "run-1"}), encoding="utf-8")
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run", side_effect=OSError("code not found"))
    def test_returns_false_when_code_command_fails(self, mock_subprocess, mock_env, tmp_path):
        """Returns False when subprocess.run raises OSError."""
        _write_marker(tmp_path)
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree", return_value=(None, ""))
    def test_returns_false_when_state_context_unavailable(self, mock_resolve, mock_subprocess, mock_env, tmp_path):
        """Returns False when state file path cannot be resolved."""
        _write_marker(tmp_path)
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    @patch("agentic_devtools.cli.copilot.auto_start._is_run_triggered", return_value=True)
    @patch(f"{_MODULE}._cleanup_pending_auto_start_marker")
    def test_returns_true_when_run_id_confirmed(
        self, mock_cleanup, mock_triggered, mock_subprocess, mock_env, tmp_path
    ):
        """Returns True when the run ID is confirmed after sendSequence."""
        _write_marker(tmp_path, run_id="run-confirmed")
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-confirmed"),
        ):
            result = _try_terminal_send_fallback(str(tmp_path))
        assert result is True
        mock_cleanup.assert_called_once_with(str(tmp_path))

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    @patch("agentic_devtools.cli.copilot.auto_start._is_run_triggered", return_value=False)
    @patch("time.sleep")
    def test_returns_false_after_timeout_when_run_id_not_confirmed(
        self, mock_sleep, mock_triggered, mock_subprocess, mock_env, tmp_path
    ):
        """Returns False when run ID is not confirmed within the wait window."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-1"),
        ):
            result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    def test_includes_model_in_command_when_present(self, mock_subprocess, mock_env, tmp_path):
        """When model is present in marker, --model flag is included in the command."""
        _write_marker(tmp_path, model="gpt-4")
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-1"),
        ):
            with patch(
                "agentic_devtools.cli.copilot.auto_start._is_run_triggered",
                return_value=True,
            ):
                with patch(f"{_MODULE}._cleanup_pending_auto_start_marker"):
                    _try_terminal_send_fallback(str(tmp_path))

        # Verify that subprocess.run was called with --model in the command
        call_args = mock_subprocess.call_args
        send_sequence_arg = call_args[0][0][3]  # The JSON argument
        parsed = json.loads(send_sequence_arg)
        assert "--model" in parsed["text"]
        assert "gpt-4" in parsed["text"]

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    def test_does_not_include_model_when_none(self, mock_subprocess, mock_env, tmp_path):
        """When model is None in marker, --model flag is not included."""
        _write_marker(tmp_path, model=None)
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-1"),
        ):
            with patch(
                "agentic_devtools.cli.copilot.auto_start._is_run_triggered",
                return_value=True,
            ):
                with patch(f"{_MODULE}._cleanup_pending_auto_start_marker"):
                    _try_terminal_send_fallback(str(tmp_path))

        call_args = mock_subprocess.call_args
        send_sequence_arg = call_args[0][0][3]
        parsed = json.loads(send_sequence_arg)
        assert "--model" not in parsed["text"]

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_returns_false_when_marker_is_not_a_dict(self, mock_env, tmp_path):
        """Returns False when marker file contains a non-dict JSON value."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        (vscode_dir / _PENDING_AUTO_START_FILENAME).write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        result = _try_terminal_send_fallback(str(tmp_path))
        assert result is False

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    def test_returns_false_when_expected_run_id_does_not_match_marker(self, mock_env, tmp_path, capsys):
        """Returns False when expected_run_id does not match the marker's run_id."""
        _write_marker(tmp_path, run_id="old-stale-run")
        result = _try_terminal_send_fallback(str(tmp_path), expected_run_id="current-run-id")
        assert result is False
        captured = capsys.readouterr()
        assert "does not match expected run_id" in captured.out
        assert "old-stale-run" in captured.out
        assert "current-run-id" in captured.out

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    @patch("agentic_devtools.cli.copilot.auto_start._is_run_triggered", return_value=True)
    @patch(f"{_MODULE}._cleanup_pending_auto_start_marker")
    def test_succeeds_when_expected_run_id_matches_marker(
        self, mock_cleanup, mock_triggered, mock_subprocess, mock_env, tmp_path
    ):
        """Returns True when expected_run_id matches the marker's run_id."""
        _write_marker(tmp_path, run_id="matching-run")
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "matching-run"),
        ):
            result = _try_terminal_send_fallback(str(tmp_path), expected_run_id="matching-run")
        assert result is True

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}.subprocess.run")
    def test_calls_code_command_with_send_sequence(self, mock_subprocess, mock_env, tmp_path):
        """Verifies subprocess.run is called with the correct code --command args."""
        _write_marker(tmp_path)
        state_file = tmp_path / "state.json"
        state_file.write_text("{}", encoding="utf-8")
        with patch(
            f"{_MODULE}._resolve_state_context_in_worktree",
            return_value=(state_file, "run-1"),
        ):
            with patch(
                "agentic_devtools.cli.copilot.auto_start._is_run_triggered",
                return_value=True,
            ):
                with patch(f"{_MODULE}._cleanup_pending_auto_start_marker"):
                    _try_terminal_send_fallback(str(tmp_path))

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "code"
        assert cmd[1] == "--command"
        assert cmd[2] == "workbench.action.terminal.sendSequence"
        # Fourth arg should be valid JSON with a text field
        parsed = json.loads(cmd[3])
        assert "text" in parsed
        assert "agdt-copilot-auto-start" in parsed["text"]
        assert parsed["text"].endswith("\n")
