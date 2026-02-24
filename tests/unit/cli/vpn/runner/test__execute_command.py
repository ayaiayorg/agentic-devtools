"""Tests for agentic_devtools.cli.vpn.runner._execute_command."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.vpn.runner import _execute_command


class TestExecuteCommand:
    """Tests for _execute_command function."""

    @patch("agentic_devtools.cli.vpn.runner.subprocess.run")
    def test_shell_true_with_stdout(self, mock_run):
        """Test _execute_command with shell=True returns stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="hello\n", stderr="")

        rc, stdout, stderr = _execute_command("echo hello", shell=True)

        assert rc == 0
        assert stdout == "hello\n"
        assert stderr == ""
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs.get("shell") is True or call_kwargs[1].get("shell") is True

    @patch("agentic_devtools.cli.vpn.runner.subprocess.run")
    def test_shell_false_splits_command(self, mock_run):
        """Test _execute_command with shell=False splits command into args."""
        mock_run.return_value = MagicMock(returncode=0, stdout="output", stderr="")

        rc, stdout, _ = _execute_command("echo hello world", shell=False)

        assert rc == 0
        assert stdout == "output"
        # Verify it was called with a list, not a string
        call_args = mock_run.call_args[0][0]
        assert isinstance(call_args, list)
        assert call_args == ["echo", "hello", "world"]

    @patch("agentic_devtools.cli.vpn.runner.subprocess.run")
    def test_with_stderr_output(self, mock_run):
        """Test _execute_command returns stderr when present."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")

        rc, stdout, stderr = _execute_command("bad_cmd", shell=True)

        assert rc == 1
        assert stdout == ""
        assert stderr == "error message"

    @patch("agentic_devtools.cli.vpn.runner.subprocess.run")
    def test_exception_returns_error_tuple(self, mock_run):
        """Test _execute_command returns error tuple on exception."""
        mock_run.side_effect = OSError("command not found")

        rc, stdout, stderr = _execute_command("nonexistent_cmd", shell=False)

        assert rc == 1
        assert stdout == ""
        assert "command not found" in stderr
