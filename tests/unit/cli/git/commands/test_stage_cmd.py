"""Tests for agentic_devtools.cli.git.commands.stage_cmd."""

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestStageCommand:
    """Tests for stage_cmd command."""

    def test_stage_cmd(self, temp_state_dir, clear_state_before, mock_run_safe):
        """Test stage command."""
        commands.stage_cmd()
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "add", "."]

    def test_stage_cmd_dry_run(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test stage command dry run."""
        state.set_value("dry_run", True)
        commands.stage_cmd()
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
