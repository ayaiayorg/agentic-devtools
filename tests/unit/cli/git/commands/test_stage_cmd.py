"""Tests for agentic_devtools.cli.git.commands.stage_cmd."""

from unittest.mock import patch

from agentic_devtools import state
from agentic_devtools.agdt_gitignore import AGDT_GITIGNORE_ENTRIES
from agentic_devtools.cli.git import commands, operations


class TestStageCommand:
    """Tests for stage_cmd command."""

    def test_stage_cmd(self, temp_state_dir, clear_state_before, mock_run_safe):
        """Test stage command."""
        with patch.object(operations, "get_current_branch", return_value="main"):
            commands.stage_cmd()
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        # 1 (git add .) + n (STAGE_EXCLUDE_FILES) + m (AGDT_GITIGNORE_ENTRIES resets)
        assert mock_run_safe.call_count == 1 + n + m
        # First call: git add .
        assert mock_run_safe.call_args_list[0][0][0] == ["git", "add", "."]
        # Subsequent calls: git reset HEAD -- <excluded> for each excluded file
        for i, excluded in enumerate(operations.STAGE_EXCLUDE_FILES):
            assert mock_run_safe.call_args_list[1 + i][0][0] == ["git", "reset", "HEAD", "--", excluded]

    def test_stage_cmd_dry_run(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test stage command dry run."""
        state.set_value("dry_run", True)
        with patch.object(operations, "get_current_branch", return_value="main"):
            commands.stage_cmd()
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
