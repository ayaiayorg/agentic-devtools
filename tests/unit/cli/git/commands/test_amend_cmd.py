"""Tests for agentic_devtools.cli.git.commands.amend_cmd."""

from unittest.mock import MagicMock

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestAmendCommand:
    """Tests for amend_cmd command."""

    def test_amend_cmd_full_workflow(self, temp_state_dir, clear_state_before, mock_run_safe):
        """Test full amend workflow."""
        state.set_value("commit_message", "Updated commit")

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="", stderr=""),  # amend
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        commands.amend_cmd()

        assert mock_run_safe.call_count == 3

    def test_amend_cmd_skip_stage(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test amend with skip_stage."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("skip_stage", True)

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # amend
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        commands.amend_cmd()

        assert mock_run_safe.call_count == 2
        captured = capsys.readouterr()
        assert "Skipping stage" in captured.out

    def test_amend_cmd_skip_push(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test amend with skip_push."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("skip_push", True)

        commands.amend_cmd()

        assert mock_run_safe.call_count == 2
        captured = capsys.readouterr()
        assert "Skipping push" in captured.out

    def test_amend_cmd_dry_run(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test amend dry run."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("dry_run", True)

        commands.amend_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "No changes were made" in captured.out

    def test_amend_cmd_dry_run_skip_push_shows_message(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test that skip_push message shows in dry_run mode."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("dry_run", True)
        state.set_value("skip_push", True)

        commands.amend_cmd()

        captured = capsys.readouterr()
        assert "Skipping push" in captured.out
