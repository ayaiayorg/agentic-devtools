"""Tests for _focus_vscode_window."""

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import _focus_vscode_window

_MODULE = "agentic_devtools.cli.workflows.worktree_setup"


class TestFocusVscodeWindow:
    """Tests for the _focus_vscode_window helper."""

    @patch(f"{_MODULE}.subprocess.run", return_value=MagicMock(returncode=0))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_returns_true_when_code_exits_zero(self, mock_find, mock_run, tmp_path):
        """Returns True when 'code' exits with returncode 0."""
        result = _focus_vscode_window(str(tmp_path))
        assert result is True

    @patch(f"{_MODULE}.subprocess.run", return_value=MagicMock(returncode=1))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_returns_false_when_code_exits_nonzero(self, mock_find, mock_run, tmp_path, capsys):
        """Returns False when 'code' exits with non-zero returncode."""
        result = _focus_vscode_window(str(tmp_path))
        assert result is False
        captured = capsys.readouterr()
        assert "exited with code 1" in captured.out

    @patch(f"{_MODULE}.subprocess.run", side_effect=OSError("code not found"))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_returns_false_on_oserror(self, mock_find, mock_run, tmp_path, capsys):
        """Returns False when subprocess.run raises OSError."""
        result = _focus_vscode_window(str(tmp_path))
        assert result is False
        captured = capsys.readouterr()
        assert "failed or timed out" in captured.out

    @patch(f"{_MODULE}.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="code", timeout=10))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_returns_false_on_timeout(self, mock_find, mock_run, tmp_path, capsys):
        """Returns False when subprocess.run raises TimeoutExpired."""
        result = _focus_vscode_window(str(tmp_path))
        assert result is False
        captured = capsys.readouterr()
        assert "failed or timed out" in captured.out

    @patch(f"{_MODULE}.subprocess.run", return_value=MagicMock(returncode=0))
    @patch(f"{_MODULE}.find_workspace_file", return_value="/path/to/workspace.code-workspace")
    def test_uses_workspace_file_when_found(self, mock_find, mock_run, tmp_path):
        """Uses workspace file path when find_workspace_file returns one."""
        _focus_vscode_window(str(tmp_path))
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd == ["code", "/path/to/workspace.code-workspace"]

    @patch(f"{_MODULE}.subprocess.run", return_value=MagicMock(returncode=0))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_uses_worktree_path_when_no_workspace_file(self, mock_find, mock_run, tmp_path):
        """Uses worktree folder path when find_workspace_file returns None."""
        _focus_vscode_window(str(tmp_path))
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd == ["code", str(tmp_path)]

    @patch(f"{_MODULE}.platform.system", return_value="Windows")
    @patch(f"{_MODULE}.subprocess.run", return_value=MagicMock(returncode=0))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_uses_shell_true_on_windows(self, mock_find, mock_run, mock_platform, tmp_path):
        """Uses shell=True on Windows."""
        _focus_vscode_window(str(tmp_path))
        call_args = mock_run.call_args
        assert call_args[1]["shell"] is True

    @patch(f"{_MODULE}.platform.system", return_value="Linux")
    @patch(f"{_MODULE}.subprocess.run", return_value=MagicMock(returncode=0))
    @patch(f"{_MODULE}.find_workspace_file", return_value=None)
    def test_uses_shell_false_on_non_windows(self, mock_find, mock_run, mock_platform, tmp_path):
        """Uses shell=False on non-Windows platforms."""
        _focus_vscode_window(str(tmp_path))
        call_args = mock_run.call_args
        assert call_args[1]["shell"] is False
