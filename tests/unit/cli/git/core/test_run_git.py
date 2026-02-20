"""Tests for agentic_devtools.cli.git.core.run_git."""

import pytest

from agentic_devtools.cli.git import core


class TestRunGit:
    """Tests for git command execution."""

    def test_run_git_success(self, mock_run_safe):
        """Test successful git command."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=0, stdout="output", stderr="")
        result = core.run_git("status")
        mock_run_safe.assert_called_once()
        assert result.returncode == 0

    def test_run_git_failure_exits(self, mock_run_safe):
        """Test git command failure causes exit."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error message")
        with pytest.raises(SystemExit) as exc_info:
            core.run_git("bad-command")
        assert exc_info.value.code == 1

    def test_run_git_failure_prints_stderr(self, mock_run_safe, capsys):
        """Test git command failure prints stderr output."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repository")
        with pytest.raises(SystemExit):
            core.run_git("status")
        captured = capsys.readouterr()
        assert "fatal: not a git repository" in captured.err

    def test_run_git_failure_without_stderr(self, mock_run_safe, capsys):
        """Test git command failure with empty stderr."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="")
        with pytest.raises(SystemExit):
            core.run_git("bad-command")
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    def test_run_git_failure_with_check_false_returns_result(self, mock_run_safe):
        """Test that check=False returns result instead of exiting."""
        from unittest.mock import MagicMock

        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = core.run_git("bad-command", check=False)
        assert result.returncode == 1

    def test_run_git_constructs_correct_command(self, mock_run_safe):
        """Test that command is constructed correctly."""
        core.run_git("commit", "-m", "message")
        called_cmd = mock_run_safe.call_args[0][0]
        assert called_cmd == ["git", "commit", "-m", "message"]
