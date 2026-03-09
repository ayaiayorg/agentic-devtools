"""Tests for agentic_devtools.cli.git.agdt_branch._run_plumbing."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.agdt_branch import _run_plumbing


class TestRunPlumbing:
    """Tests for the _run_plumbing helper."""

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_prepends_git(self, mock_run):
        """_run_plumbing prepends 'git' to the command list."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_plumbing("status")
        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "status"]

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_passes_shell_false(self, mock_run):
        """_run_plumbing always passes shell=False."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_plumbing("rev-parse", "HEAD")
        kwargs = mock_run.call_args[1]
        assert kwargs["shell"] is False

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_captures_output(self, mock_run):
        """_run_plumbing passes capture_output=True and text=True."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_plumbing("log")
        kwargs = mock_run.call_args[1]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_forwards_extra_kwargs(self, mock_run):
        """_run_plumbing forwards extra keyword arguments (e.g. env)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        custom_env = {"GIT_INDEX_FILE": "/tmp/idx"}
        _run_plumbing("write-tree", env=custom_env)
        kwargs = mock_run.call_args[1]
        assert kwargs["env"] is custom_env

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_returns_completed_process(self, mock_run):
        """_run_plumbing returns the CompletedProcess from run_safe."""
        expected = MagicMock(returncode=0, stdout="abc\n", stderr="")
        mock_run.return_value = expected
        result = _run_plumbing("hash-object", "-w", "/tmp/f")
        assert result is expected

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_strips_security_critical_kwargs(self, mock_run):
        """_run_plumbing ignores caller attempts to override shell/text/capture_output."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _run_plumbing("status", shell=True, text=False, capture_output=False)
        kwargs = mock_run.call_args[1]
        assert kwargs["shell"] is False
        assert kwargs["text"] is True
        assert kwargs["capture_output"] is True
