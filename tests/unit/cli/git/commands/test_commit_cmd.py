"""Tests for agentic_devtools.cli.git.commands.commit_cmd."""

import sys
from unittest.mock import MagicMock, patch

from agentic_devtools import state
from agentic_devtools.cli.git import commands, operations


class TestCommitCommand:
    """Tests for commit_cmd command (new commit workflow)."""

    def test_commit_cmd_full_workflow(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main
    ):
        """Test full commit workflow (with sync mocked)."""
        state.set_value("commit_message", "Test commit")

        n = len(operations.STAGE_EXCLUDE_FILES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        commands.commit_cmd()

        assert mock_run_safe.call_count == 4 + n
        mock_sync_with_main.assert_called_once()

    def test_commit_cmd_skip_stage(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test commit with skip_stage."""
        state.set_value("commit_message", "Test commit")
        state.set_value("skip_stage", True)

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        commands.commit_cmd()

        assert mock_run_safe.call_count == 3
        captured = capsys.readouterr()
        assert "Skipping stage" in captured.out

    def test_commit_cmd_skip_push(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test commit with skip_push."""
        state.set_value("commit_message", "Test commit")
        state.set_value("skip_push", True)

        commands.commit_cmd()

        assert mock_run_safe.call_count == 2 + len(operations.STAGE_EXCLUDE_FILES)
        captured = capsys.readouterr()
        assert "Skipping push" in captured.out

    def test_commit_cmd_dry_run(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test commit dry run."""
        state.set_value("commit_message", "Test commit")
        state.set_value("dry_run", True)

        commands.commit_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "No changes were made" in captured.out

    def test_commit_cmd_dry_run_skip_push_shows_message(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test that skip_push message shows in dry_run mode."""
        state.set_value("commit_message", "Test commit")
        state.set_value("dry_run", True)
        state.set_value("skip_push", True)

        commands.commit_cmd()

        captured = capsys.readouterr()
        assert "Skipping push" in captured.out

    def test_commit_cmd_force_push_after_rebase(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, capsys
    ):
        """Test that force push is used when rebase occurs, even for new commits."""
        state.set_value("commit_message", "Test commit")

        n = len(operations.STAGE_EXCLUDE_FILES)
        with patch("agentic_devtools.cli.git.commands._sync_with_main", return_value=True):
            mock_run_safe.side_effect = (
                [MagicMock(returncode=0, stdout="", stderr="")]  # add
                + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
                + [
                    MagicMock(returncode=0, stdout="", stderr=""),  # commit
                    MagicMock(returncode=0, stdout="", stderr=""),  # force push
                ]
            )

            commands.commit_cmd()

            assert mock_run_safe.call_count == 3 + n
            captured = capsys.readouterr()
            assert "Force pushing" in captured.out

    def test_commit_uses_amend_when_should_amend(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_sync_with_main
    ):
        """Test that commit cmd uses amend when should_amend_instead_of_commit returns True."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("jira.issue_key", "DFLY-1234")

        n = len(operations.STAGE_EXCLUDE_FILES)
        with patch("agentic_devtools.cli.git.commands.should_amend_instead_of_commit") as mock_should:
            mock_should.return_value = True
            mock_run_safe.side_effect = (
                [MagicMock(returncode=0, stdout="", stderr="")]  # add
                + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
                + [
                    MagicMock(returncode=0, stdout="", stderr=""),  # amend
                    MagicMock(returncode=0, stdout="", stderr=""),  # force push
                ]
            )

            commands.commit_cmd()

            assert mock_run_safe.call_count == 3 + n
            # Amend call is at index 1 + n (after add + N resets)
            amend_call_args = mock_run_safe.call_args_list[1 + n][0][0]
            assert "--amend" in amend_call_args

    def test_commit_uses_new_commit_when_should_not_amend(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_sync_with_main
    ):
        """Test that commit cmd uses new commit when should_amend returns False."""
        state.set_value("commit_message", "New commit")
        state.set_value("jira.issue_key", "DFLY-1234")

        n = len(operations.STAGE_EXCLUDE_FILES)
        with patch("agentic_devtools.cli.git.commands.should_amend_instead_of_commit") as mock_should:
            mock_should.return_value = False
            mock_run_safe.side_effect = (
                [MagicMock(returncode=0, stdout="", stderr="")]  # add
                + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
                + [
                    MagicMock(returncode=0, stdout="", stderr=""),  # commit
                    MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
                    MagicMock(returncode=0, stdout="", stderr=""),  # push
                ]
            )

            commands.commit_cmd()

            assert mock_run_safe.call_count == 4 + n
            # Commit call is at index 1 + n (after add + N resets)
            commit_call_args = mock_run_safe.call_args_list[1 + n][0][0]
            assert "--amend" not in commit_call_args

    def test_commit_with_completed_marks_items(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test that --completed parameter marks checklist items."""
        state.set_value("commit_message", "Test commit")
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1234",
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": False},
                        {"id": 2, "text": "Task 2", "completed": False},
                    ],
                    "modified_by_agent": False,
                },
            },
        )

        n = len(operations.STAGE_EXCLUDE_FILES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        with patch.object(sys, "argv", ["agdt-git-save-work", "--completed", "1,2"]):
            commands.commit_cmd()

        from agentic_devtools.cli.workflows.checklist import get_checklist

        checklist = get_checklist()
        assert checklist is not None
        assert checklist.items[0].completed is True
        assert checklist.items[1].completed is True

        captured = capsys.readouterr()
        assert "Marked checklist items as completed" in captured.out

    def test_commit_completed_triggers_implementation_review(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test that completing all items triggers implementation-review transition."""
        state.set_value("commit_message", "Test commit")
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1234",
                "checklist": {
                    "items": [{"id": 1, "text": "Task 1", "completed": False}],
                    "modified_by_agent": False,
                },
            },
        )

        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * len(operations.STAGE_EXCLUDE_FILES)  # resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        with patch.object(sys, "argv", ["agdt-git-save-work", "--completed", "1"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        assert "All checklist items complete" in captured.out
