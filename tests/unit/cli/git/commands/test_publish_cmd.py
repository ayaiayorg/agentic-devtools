"""Tests for agentic_devtools.cli.git.commands.publish_cmd."""

from unittest.mock import MagicMock

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestPublishCommand:
    """Tests for publish_cmd command."""

    def test_publish_cmd(self, temp_state_dir, clear_state_before, mock_run_safe):
        """Test publish command."""
        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="feature/test\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        commands.publish_cmd()

        assert mock_run_safe.call_count == 2

    def test_publish_cmd_dry_run(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test publish command dry run."""
        state.set_value("dry_run", True)
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature/test\n", stderr="")

        commands.publish_cmd()

        assert mock_run_safe.call_count == 1
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
