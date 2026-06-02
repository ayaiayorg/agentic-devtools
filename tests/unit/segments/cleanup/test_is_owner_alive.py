"""Tests for _is_owner_alive helper."""

import os
from unittest.mock import patch

from agentic_devtools.segments.cleanup import _is_owner_alive


class TestIsOwnerAlive:
    """Tests for _is_owner_alive function."""

    def test_current_process_alive(self):
        """Current process PID reports as alive."""
        assert _is_owner_alive(os.getpid()) is True

    def test_invalid_pid_zero(self):
        """PID 0 reports as not alive."""
        assert _is_owner_alive(0) is False

    def test_negative_pid(self):
        """Negative PID reports as not alive."""
        assert _is_owner_alive(-1) is False

    def test_nonexistent_pid(self):
        """Very large PID that likely doesn't exist reports as not alive."""
        # Use a very high PID unlikely to exist
        assert _is_owner_alive(4000000) is False

    @patch("agentic_devtools.segments.cleanup.sys.platform", "linux")
    @patch("os.kill", side_effect=OSError("No such process"))
    def test_oserror_returns_false(self, mock_kill):
        """OSError from os.kill returns False."""
        assert _is_owner_alive(99999) is False

    @patch("agentic_devtools.segments.cleanup.sys.platform", "linux")
    @patch("os.kill", side_effect=PermissionError("Operation not permitted"))
    def test_permission_error_returns_true(self, mock_kill):
        """PermissionError from os.kill returns True (process likely exists)."""
        assert _is_owner_alive(99999) is True

    @patch("agentic_devtools.segments.cleanup.sys.platform", "win32")
    @patch("ctypes.WinDLL", create=True)
    def test_windows_uses_pointer_sized_handle_signatures(self, mock_windll):
        """Windows branch configures OpenProcess/CloseHandle with HANDLE signatures."""

        class FakeFunction:
            def __init__(self, return_value):
                self.return_value = return_value
                self.argtypes = None
                self.restype = None
                self.calls = []

            def __call__(self, *args):
                self.calls.append(args)
                return self.return_value

        class FakeKernel32:
            def __init__(self):
                self.OpenProcess = FakeFunction(0x123456789)
                self.CloseHandle = FakeFunction(1)

        fake_kernel32 = FakeKernel32()
        mock_windll.return_value = fake_kernel32

        assert _is_owner_alive(12345) is True
        assert fake_kernel32.OpenProcess.calls == [(0x1000, False, 12345)]
        assert fake_kernel32.CloseHandle.calls == [(0x123456789,)]
        assert fake_kernel32.OpenProcess.argtypes[2].__name__ == "c_ulong"
        assert fake_kernel32.OpenProcess.restype.__name__ == "c_void_p"
        assert fake_kernel32.CloseHandle.argtypes[0].__name__ == "c_void_p"
