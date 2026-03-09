"""Tests for agentic_devtools.cli.git.agdt_branch.push_branch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.agdt_branch import push_branch


class TestPushBranch:
    """Tests for the push_branch function."""

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_returns_completed_process(self, mock_run):
        """push_branch returns the CompletedProcess from run_safe."""
        expected = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.return_value = expected
        result = push_branch("my-branch")
        assert result is expected

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_calls_git_push_origin(self, mock_run):
        """push_branch invokes git push origin <branch>."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        push_branch("my-branch")
        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "push", "origin", "my-branch"]

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_does_not_raise_on_failure(self, mock_run):
        """push_branch does not raise when git push fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="rejected")
        result = push_branch("branch")
        assert result.returncode == 1

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_captures_output(self, mock_run):
        """push_branch passes capture_output=True and text=True."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        push_branch("branch")
        kwargs = mock_run.call_args[1]
        assert kwargs.get("capture_output") is True
        assert kwargs.get("text") is True
