"""Tests for _is_process_alive."""

import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.copilot.session import _is_process_alive


class TestIsProcessAlive:
    """Tests for _is_process_alive utility."""

    STILL_ACTIVE = 259
    EXITED_SUCCESSFULLY = 0

    def test_invalid_pid_zero(self):
        """PID 0 returns False."""
        assert _is_process_alive(0) is False

    def test_invalid_pid_negative(self):
        """Negative PID returns False."""
        assert _is_process_alive(-1) is False

    def test_current_process_alive(self):
        """Current process PID is alive."""
        assert _is_process_alive(os.getpid()) is True

    def test_dead_process(self):
        """Exited subprocess PID returns False."""
        proc = subprocess.Popen([sys.executable, "-c", "pass"])
        proc.wait(timeout=5)
        assert _is_process_alive(proc.pid) is False

    @patch("os.kill", side_effect=ProcessLookupError)
    def test_unix_dead_process(self, mock_kill):
        """ProcessLookupError means dead on Unix."""
        assert _is_process_alive(12345) is False

    @patch("os.kill", side_effect=PermissionError)
    def test_unix_permission_error_means_alive(self, mock_kill):
        """PermissionError means process exists but not owned — alive."""
        assert _is_process_alive(12345) is True

    @patch("os.kill", side_effect=OSError("unexpected"))
    def test_unix_generic_os_error(self, mock_kill):
        """Generic OSError returns False."""
        assert _is_process_alive(12345) is False

    def test_windows_access_denied_means_alive(self):
        """Windows ERROR_ACCESS_DENIED means process exists — alive."""
        kernel32 = MagicMock()
        kernel32.OpenProcess.return_value = 0

        with patch("agentic_devtools.cli.copilot.session.sys.platform", "win32"):
            with patch("ctypes.WinDLL", return_value=kernel32, create=True):
                with patch("ctypes.get_last_error", return_value=5, create=True):
                    assert _is_process_alive(12345) is True

    def test_windows_running_process_returns_true(self):
        """Windows returns True when process exit code is STILL_ACTIVE."""
        kernel32 = MagicMock()
        kernel32.OpenProcess.return_value = 123

        def set_running_exit_code(_handle, exit_code_ptr):
            exit_code_ptr._obj.value = self.STILL_ACTIVE
            return 1

        kernel32.GetExitCodeProcess.side_effect = set_running_exit_code

        with patch("agentic_devtools.cli.copilot.session.sys.platform", "win32"):
            with patch("ctypes.WinDLL", return_value=kernel32, create=True):
                assert _is_process_alive(12345) is True

        kernel32.CloseHandle.assert_called_once_with(123)

    def test_windows_exited_process_returns_false(self):
        """Windows returns False when process has exited."""
        kernel32 = MagicMock()
        kernel32.OpenProcess.return_value = 123

        def set_exited_exit_code(_handle, exit_code_ptr):
            # 0 indicates a process that has exited successfully.
            exit_code_ptr._obj.value = self.EXITED_SUCCESSFULLY
            return 1

        kernel32.GetExitCodeProcess.side_effect = set_exited_exit_code

        with patch("agentic_devtools.cli.copilot.session.sys.platform", "win32"):
            with patch("ctypes.WinDLL", return_value=kernel32, create=True):
                assert _is_process_alive(12345) is False

        kernel32.CloseHandle.assert_called_once_with(123)

    def test_windows_get_exit_code_access_denied_means_alive(self):
        """Windows ERROR_ACCESS_DENIED from GetExitCodeProcess means alive."""
        kernel32 = MagicMock()
        kernel32.OpenProcess.return_value = 123
        kernel32.GetExitCodeProcess.return_value = 0

        with patch("agentic_devtools.cli.copilot.session.sys.platform", "win32"):
            with patch("ctypes.WinDLL", return_value=kernel32, create=True):
                with patch("ctypes.get_last_error", return_value=5, create=True):
                    assert _is_process_alive(12345) is True

        kernel32.CloseHandle.assert_called_once_with(123)

    @patch("os.kill", side_effect=OverflowError)
    def test_unix_overflow_pid_returns_false(self, mock_kill):
        """OverflowError from os.kill for an out-of-range PID returns False."""
        assert _is_process_alive(99999999999) is False

    def test_windows_overflow_pid_returns_false(self):
        """OverflowError during OpenProcess for an out-of-range PID returns False."""
        with patch("agentic_devtools.cli.copilot.session.sys.platform", "win32"):
            with patch("ctypes.WinDLL", side_effect=OverflowError, create=True):
                assert _is_process_alive(99999999999) is False
