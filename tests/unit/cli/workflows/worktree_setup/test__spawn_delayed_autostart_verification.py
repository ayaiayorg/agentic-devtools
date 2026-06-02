"""Tests for _spawn_delayed_autostart_verification."""

from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, patch

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


class TestSpawnDelayedAutostartVerification:
    """Unit tests for _spawn_delayed_autostart_verification."""

    def _import_fn(self):
        from agentic_devtools.cli.workflows.worktree_setup import (
            _spawn_delayed_autostart_verification,
        )

        return _spawn_delayed_autostart_verification

    def _join_verification_thread(self, timeout: float = 5.0) -> None:
        deadline = threading.Event()
        wait_s = 0.01
        elapsed = 0.0
        while elapsed < timeout:
            for thread in threading.enumerate():
                if thread.name == "autostart-verification":
                    thread.join(timeout=max(0.0, timeout - elapsed))
                    return
            deadline.wait(wait_s)
            elapsed += wait_s

    @patch(f"{_MODULE}._in_test_environment", return_value=True)
    def test_noop_in_test_environment(self, mock_test_env):
        """Verify function is a no-op when _in_test_environment returns True."""
        fn = self._import_fn()

        # Should return immediately without spawning a thread
        fn(
            worktree_path="/tmp/fake",
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        # No thread should be running with our name
        threads = [t for t in threading.enumerate() if t.name == "autostart-verification"]
        assert threads == []

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    @patch("agentic_devtools.cli.copilot.auto_start._is_run_triggered", return_value=True)
    @patch(f"{_MODULE}._AUTOSTART_VERIFICATION_DELAY_S", 0.01)
    @patch(f"{_MODULE}._AUTOSTART_VERIFICATION_POLL_S", 0.005)
    def test_returns_early_when_run_triggered(self, mock_triggered, mock_resolve, mock_test_env, tmp_path):
        """Verify thread exits without starting fallback when auto-start task ran."""
        fn = self._import_fn()
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pending_marker = tmp_path / ".vscode" / "pending-auto-start.json"
        pending_marker.parent.mkdir(parents=True)
        pending_marker.write_text('{"run_id":"run-123"}', encoding="utf-8")
        mock_resolve.return_value = (state_file, "")

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        # _is_run_triggered was called and returned True — no fallback
        mock_triggered.assert_called()

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}._open_log_in_vscode")
    @patch(f"{_MODULE}.is_vscode_available", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_starts_fallback_when_no_state_file(
        self,
        mock_resolve,
        mock_copilot,
        mock_vscode,
        mock_open_log,
        mock_test_env,
        tmp_path,
    ):
        """Verify fallback session starts when state file cannot be resolved."""
        fn = self._import_fn()
        mock_resolve.return_value = (None, "")
        mock_copilot.return_value = None

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        mock_copilot.assert_called_once()

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}._open_log_in_vscode")
    @patch(f"{_MODULE}.is_vscode_available", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    @patch("agentic_devtools.cli.copilot.auto_start._is_run_triggered", return_value=False)
    @patch(f"{_MODULE}._AUTOSTART_VERIFICATION_DELAY_S", 0.01)
    @patch(f"{_MODULE}._AUTOSTART_VERIFICATION_POLL_S", 0.005)
    def test_starts_fallback_after_timeout(
        self,
        mock_triggered,
        mock_resolve,
        mock_copilot,
        mock_vscode,
        mock_open_log,
        mock_test_env,
        tmp_path,
    ):
        """Verify fallback session starts when polling times out."""
        fn = self._import_fn()
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pending_marker = tmp_path / ".vscode" / "pending-auto-start.json"
        pending_marker.parent.mkdir(parents=True)
        pending_marker.write_text('{"run_id":"run-456"}', encoding="utf-8")
        mock_resolve.return_value = (state_file, "")
        mock_copilot.return_value = None

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        mock_copilot.assert_called_once()

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    @patch("agentic_devtools.cli.copilot.auto_start._is_run_triggered", return_value=False)
    @patch(f"{_MODULE}._AUTOSTART_VERIFICATION_DELAY_S", 0.01)
    @patch(f"{_MODULE}._AUTOSTART_VERIFICATION_POLL_S", 0.005)
    def test_pins_state_dir_for_fallback_session(
        self,
        mock_triggered,
        mock_resolve,
        mock_copilot,
        mock_test_env,
        tmp_path,
    ):
        """Fallback session temporarily pins AGENTIC_DEVTOOLS_STATE_DIR to target state dir."""
        fn = self._import_fn()
        state_dir = tmp_path / ".agdt-state"
        state_dir.mkdir()
        state_file = state_dir / "state.json"
        state_file.write_text("{}")
        mock_resolve.return_value = (state_file, "")

        pending_marker = tmp_path / ".vscode" / "pending-auto-start.json"
        pending_marker.parent.mkdir(parents=True)
        pending_marker.write_text('{"run_id":"run-456"}', encoding="utf-8")

        original_state_dir = "/tmp/original-state-dir"
        with patch.dict(os.environ, {"AGENTIC_DEVTOOLS_STATE_DIR": original_state_dir}, clear=False):
            observed: dict[str, str | None] = {}

            def _capture_state_dir(**kwargs):
                observed["during_call"] = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
                return None

            mock_copilot.side_effect = _capture_state_dir

            fn(
                worktree_path=str(tmp_path),
                start_prompt="test prompt",
                workflow_name="test-workflow",
            )

            self._join_verification_thread()

            assert observed["during_call"] == str(state_dir)
            assert os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR") == original_state_dir

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}._open_log_in_vscode")
    @patch(f"{_MODULE}.is_vscode_available", return_value=True)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_opens_log_when_vscode_available(
        self,
        mock_resolve,
        mock_copilot,
        mock_vscode,
        mock_open_log,
        mock_test_env,
        tmp_path,
    ):
        """Verify _open_log_in_vscode is called when session has a log file."""
        fn = self._import_fn()
        mock_resolve.return_value = (None, "")

        session_result = MagicMock()
        session_result.log_file = "/tmp/copilot.log"
        mock_copilot.return_value = session_result

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        mock_open_log.assert_called_once_with("/tmp/copilot.log", str(tmp_path))

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_handles_exception_in_fallback(
        self,
        mock_resolve,
        mock_copilot,
        mock_test_env,
        tmp_path,
        capsys,
    ):
        """Verify exception in fallback session is caught and logged."""
        fn = self._import_fn()
        mock_resolve.return_value = (None, "")
        mock_copilot.side_effect = RuntimeError("boom")

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        captured = capsys.readouterr()
        assert "delayed fallback Copilot session failed" in captured.err

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_starts_fallback_when_pending_marker_is_invalid_json(
        self,
        mock_resolve,
        mock_copilot,
        mock_test_env,
        tmp_path,
    ):
        """Verify invalid pending marker JSON falls back safely."""
        fn = self._import_fn()
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pending_marker = tmp_path / ".vscode" / "pending-auto-start.json"
        pending_marker.parent.mkdir(parents=True)
        pending_marker.write_text("{", encoding="utf-8")
        mock_resolve.return_value = (state_file, "")
        mock_copilot.return_value = None

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        mock_copilot.assert_called_once()

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_starts_fallback_when_pending_marker_run_id_not_string(
        self,
        mock_resolve,
        mock_copilot,
        mock_test_env,
        tmp_path,
    ):
        """Verify non-string run_id in pending marker falls back safely."""
        fn = self._import_fn()
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pending_marker = tmp_path / ".vscode" / "pending-auto-start.json"
        pending_marker.parent.mkdir(parents=True)
        pending_marker.write_text('{"run_id":123}', encoding="utf-8")
        mock_resolve.return_value = (state_file, "")
        mock_copilot.return_value = None

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        mock_copilot.assert_called_once()

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_starts_fallback_when_pending_marker_is_not_object(
        self,
        mock_resolve,
        mock_copilot,
        mock_test_env,
        tmp_path,
    ):
        """Verify non-object marker JSON falls back safely."""
        fn = self._import_fn()
        state_file = tmp_path / "state.json"
        state_file.write_text("{}")
        pending_marker = tmp_path / ".vscode" / "pending-auto-start.json"
        pending_marker.parent.mkdir(parents=True)
        pending_marker.write_text('["run-789"]', encoding="utf-8")
        mock_resolve.return_value = (state_file, "")
        mock_copilot.return_value = None

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        mock_copilot.assert_called_once()

    @patch(f"{_MODULE}._in_test_environment", return_value=False)
    @patch(f"{_MODULE}._open_log_in_vscode")
    @patch(f"{_MODULE}.is_vscode_available", return_value=False)
    @patch("agentic_devtools.cli.copilot.session.start_copilot_session")
    @patch(f"{_MODULE}._resolve_state_context_in_worktree")
    def test_starts_fallback_when_no_state_file_but_has_run_id(
        self,
        mock_resolve,
        mock_copilot,
        mock_vscode,
        mock_open_log,
        mock_test_env,
        tmp_path,
    ):
        """Verify fallback starts when state_file_path is None even if state_run_id is truthy."""
        fn = self._import_fn()
        # state_file_path is None, but state_run_id has a value
        mock_resolve.return_value = (None, "run-123")
        mock_copilot.return_value = None

        fn(
            worktree_path=str(tmp_path),
            start_prompt="test prompt",
            workflow_name="test-workflow",
        )

        self._join_verification_thread()

        # Should fall back immediately because state_file_path is None
        mock_copilot.assert_called_once()
