"""Tests for RunAutoExecuteCommand."""

import subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    _run_auto_execute_command,
)


class TestRunAutoExecuteCommand:
    """Tests for _run_auto_execute_command function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_zero_on_success(self, mock_run, capsys):
        """Test that exit code 0 is returned on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output text", stderr="")

        result = _run_auto_execute_command(["echo", "hello"], "/some/worktree", 300)

        assert result == 0
        mock_run.assert_called_once_with(
            ["echo", "hello"],
            cwd="/some/worktree",
            capture_output=True,
            text=True,
            timeout=300,
            shell=False,
        )

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_prints_stdout_on_success(self, mock_run, capsys):
        """Test that stdout is printed when command succeeds."""
        mock_run.return_value = MagicMock(returncode=0, stdout="hello world\n", stderr="")

        _run_auto_execute_command(["echo", "hello world"], "/some/worktree", 300)

        captured = capsys.readouterr()
        assert "hello world" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_nonzero_on_failure_and_logs_warning(self, mock_run, capsys):
        """Test that non-zero exit code is returned and warning is logged."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")

        result = _run_auto_execute_command(["false"], "/some/worktree", 300)

        assert result == 1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "1" in captured.out
        assert "error message" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_minus_one_on_timeout(self, mock_run, capsys):
        """Test that -1 is returned when command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["cmd"], timeout=10)

        result = _run_auto_execute_command(["sleep", "999"], "/some/worktree", 10)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "timed out" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_minus_one_on_file_not_found(self, mock_run, capsys):
        """Test that -1 is returned when the command executable is not found."""
        mock_run.side_effect = FileNotFoundError("No such file or directory")

        result = _run_auto_execute_command(["nonexistent-cmd"], "/some/worktree", 300)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_minus_one_on_os_error(self, mock_run, capsys):
        """Test that -1 is returned on generic OSError."""
        mock_run.side_effect = OSError("Permission denied")

        result = _run_auto_execute_command(["cmd"], "/some/worktree", 300)

        assert result == -1
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_logs_command_before_execution(self, mock_run, capsys):
        """Test that the command is logged before execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_auto_execute_command(["agdt-initiate-review", "--pr-id", "123"], "/worktree", 60)

        captured = capsys.readouterr()
        assert "agdt-initiate-review --pr-id 123" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_uses_custom_timeout(self, mock_run, capsys):
        """Test that the custom timeout is passed to subprocess.run."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        _run_auto_execute_command(["cmd"], "/worktree", 60)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 60
