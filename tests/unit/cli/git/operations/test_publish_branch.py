"""Tests for agentic_devtools.cli.git.operations.publish_branch."""

from unittest.mock import MagicMock

from agentic_devtools.cli.git import operations


class TestPublishBranch:
    """Tests for publish_branch function."""

    def test_publish_branch(self, mock_run_safe):
        """Test publishing a branch."""
        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="feature/test\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        operations.publish_branch(dry_run=False)

        assert mock_run_safe.call_count == 2
        push_cmd = mock_run_safe.call_args_list[1][0][0]
        assert push_cmd == ["git", "push", "--set-upstream", "origin", "feature/test"]

    def test_publish_branch_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows branch name."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature/test\n", stderr="")

        operations.publish_branch(dry_run=True)

        assert mock_run_safe.call_count == 1
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "feature/test" in captured.out
