"""Tests for agentic_devtools.cli.git.agdt_branch.push_branch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.agdt_branch import push_branch


class TestPushBranch:
    """Tests for the push_branch function."""

    @patch("agentic_devtools.cli.git.agdt_branch._run_plumbing")
    def test_returns_completed_process(self, mock_run):
        """push_branch returns the CompletedProcess from _run_plumbing."""
        expected = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.return_value = expected
        result = push_branch("my-branch")
        assert result is expected

    @patch("agentic_devtools.cli.git.agdt_branch._run_plumbing")
    def test_calls_git_push_origin(self, mock_run):
        """push_branch invokes _run_plumbing with push origin <branch>."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        push_branch("my-branch")
        args = mock_run.call_args[0]
        assert args == ("push", "origin", "my-branch")

    @patch("agentic_devtools.cli.git.agdt_branch._run_plumbing")
    def test_does_not_raise_on_failure(self, mock_run):
        """push_branch does not raise when git push fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="rejected")
        result = push_branch("branch")
        assert result.returncode == 1
