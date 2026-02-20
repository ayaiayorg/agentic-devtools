"""Tests for SwitchToMainBranch."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    switch_to_main_branch,
)


class TestSwitchToMainBranch:
    """Tests for switch_to_main_branch function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_true_on_success(self, mock_run):
        """Test returns True when switch succeeds."""
        mock_run.return_value = MagicMock(returncode=0)

        result = switch_to_main_branch()

        assert result is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["git", "switch", "main"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_failure(self, mock_run):
        """Test returns False when switch fails."""
        mock_run.return_value = MagicMock(returncode=1)

        result = switch_to_main_branch()

        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_os_error(self, mock_run):
        """Test returns False on OS error."""
        mock_run.side_effect = OSError("git not accessible")

        result = switch_to_main_branch()

        assert result is False
