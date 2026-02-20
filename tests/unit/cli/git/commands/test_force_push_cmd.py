"""Tests for agentic_devtools.cli.git.commands.force_push_cmd."""

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestForcePushCommand:
    """Tests for force_push_cmd command."""

    def test_force_push_cmd(self, temp_state_dir, clear_state_before, mock_run_safe):
        """Test force push command."""
        commands.force_push_cmd()
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "push", "--force-with-lease"]

    def test_force_push_cmd_dry_run(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test force push command dry run."""
        state.set_value("dry_run", True)
        commands.force_push_cmd()
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
