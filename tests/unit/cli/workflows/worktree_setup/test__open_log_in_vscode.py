"""Tests for _open_log_in_vscode."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import _open_log_in_vscode


class TestOpenLogInVscode:
    """Unit tests for _open_log_in_vscode."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_opens_log_file_successfully(self, mock_run, tmp_path, capsys):
        """Verify 'code' is called with the log file path and success message is printed."""
        mock_run.return_value = MagicMock(returncode=0)
        log_file = str(tmp_path / "session.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        mock_run.assert_called_once()
        args = mock_run.call_args
        assert args[0][0][0] == "code"
        assert args[0][0][1] == log_file
        captured = capsys.readouterr()
        assert "Opened Copilot session log in VS Code" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_prints_warning_on_nonzero_exit(self, mock_run, tmp_path, capsys):
        """Verify warning printed when 'code' exits non-zero."""
        mock_run.return_value = MagicMock(returncode=1)
        log_file = str(tmp_path / "session.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        captured = capsys.readouterr()
        assert "exited with 1" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_handles_os_error(self, mock_run, tmp_path, capsys):
        """Verify OSError is caught and warning is printed."""
        mock_run.side_effect = OSError("not found")
        log_file = str(tmp_path / "session.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        captured = capsys.readouterr()
        assert "could not open log file" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_handles_timeout(self, mock_run, tmp_path, capsys):
        """Verify TimeoutExpired is caught and warning is printed."""
        mock_run.side_effect = subprocess.TimeoutExpired("code", 10)
        log_file = str(tmp_path / "session.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        captured = capsys.readouterr()
        assert "could not open log file" in captured.err

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_uses_shell_on_windows(self, mock_run, _mock_platform, tmp_path):
        """Verify Windows uses shell=True to resolve code.cmd on PATH."""
        mock_run.return_value = MagicMock(returncode=0)
        log_file = str(tmp_path / "session.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        assert mock_run.call_args[1]["shell"] is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Linux")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_avoids_shell_on_non_windows(self, mock_run, _mock_platform, tmp_path):
        """Verify non-Windows platforms keep shell disabled."""
        mock_run.return_value = MagicMock(returncode=0)
        log_file = str(tmp_path / "session.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        assert mock_run.call_args[1]["shell"] is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system", return_value="Windows")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_refuses_windows_metachar_paths(self, mock_run, _mock_platform, tmp_path, capsys):
        """Verify Windows rejects cmd.exe metacharacter paths when shell=True."""
        log_file = str(tmp_path / "session&name.log")

        _open_log_in_vscode(log_file, str(tmp_path))

        mock_run.assert_not_called()
        captured = capsys.readouterr()
        assert "contains cmd.exe metacharacters" in captured.err
