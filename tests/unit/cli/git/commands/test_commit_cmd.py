"""Tests for agentic_devtools.cli.git.commands.commit_cmd."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.agdt_gitignore import AGDT_GITIGNORE_ENTRIES
from agentic_devtools.cli.git import commands, operations


class TestCommitCommand:
    """Tests for commit_cmd command (new commit workflow)."""

    def test_commit_cmd_full_workflow(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main
    ):
        """Test full commit workflow (with sync mocked)."""
        state.set_value("commit_message", "Test commit")

        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        commands.commit_cmd()

        assert mock_run_safe.call_count == 3 + n + m
        mock_sync_with_main.assert_called_once()

    def test_commit_cmd_skip_stage(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test commit with skip_stage."""
        state.set_value("commit_message", "Test commit")
        state.set_value("skip_stage", True)

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        commands.commit_cmd()

        assert mock_run_safe.call_count == 2
        captured = capsys.readouterr()
        assert "Skipping stage" in captured.out

    def test_commit_cmd_skip_push(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test commit with skip_push."""
        state.set_value("commit_message", "Test commit")
        state.set_value("skip_push", True)

        commands.commit_cmd()

        assert mock_run_safe.call_count == 2 + len(operations.STAGE_EXCLUDE_FILES) + len(AGDT_GITIGNORE_ENTRIES)
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

    def test_commit_cmd_dry_run_reports_force_push_intent(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, capsys
    ):
        """Test dry-run mode reports force push intent when rebase occurred."""
        state.set_value("commit_message", "Test commit")
        state.set_value("dry_run", True)

        with patch("agentic_devtools.cli.git.commands._sync_with_main", return_value=True):
            commands.commit_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Would force push" in captured.out

    def test_commit_cmd_dry_run_reports_publish_intent(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test dry-run mode reports publish intent when no rebase occurred."""
        state.set_value("commit_message", "Test commit")
        state.set_value("dry_run", True)

        commands.commit_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Would publish branch" in captured.out

    def test_commit_cmd_force_push_after_rebase(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, capsys
    ):
        """Test that force push is used when rebase occurs, even for new commits."""
        state.set_value("commit_message", "Test commit")

        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        with patch("agentic_devtools.cli.git.commands._sync_with_main", return_value=True):
            mock_run_safe.side_effect = (
                [MagicMock(returncode=0, stdout="", stderr="")]  # add
                + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
                + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
                + [
                    MagicMock(returncode=0, stdout="", stderr=""),  # commit
                    MagicMock(returncode=0, stdout="", stderr=""),  # force push
                ]
            )

            commands.commit_cmd()

            assert mock_run_safe.call_count == 3 + n + m
            captured = capsys.readouterr()
            assert "Force pushing" in captured.out

    def test_commit_uses_amend_when_should_amend(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_sync_with_main
    ):
        """Test that commit cmd uses amend when should_amend_instead_of_commit returns True."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("jira.issue_key", "PROJECT-1234")

        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        with patch("agentic_devtools.cli.git.commands.should_amend_instead_of_commit") as mock_should:
            mock_should.return_value = True
            mock_run_safe.side_effect = (
                [MagicMock(returncode=0, stdout="", stderr="")]  # add
                + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
                + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
                + [
                    MagicMock(returncode=0, stdout="", stderr=""),  # amend
                    MagicMock(returncode=0, stdout="", stderr=""),  # force push
                ]
            )

            commands.commit_cmd()

            assert mock_run_safe.call_count == 3 + n + m
            # Amend call is at index 1 + n + m (after add + N resets + M agdt resets)
            amend_call_args = mock_run_safe.call_args_list[1 + n + m][0][0]
            assert "--amend" in amend_call_args

    def test_commit_uses_new_commit_when_should_not_amend(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_sync_with_main
    ):
        """Test that commit cmd uses new commit when should_amend returns False."""
        state.set_value("commit_message", "New commit")
        state.set_value("jira.issue_key", "PROJECT-1234")

        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        with patch("agentic_devtools.cli.git.commands.should_amend_instead_of_commit") as mock_should:
            mock_should.return_value = False
            mock_run_safe.side_effect = (
                [MagicMock(returncode=0, stdout="", stderr="")]  # add
                + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
                + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
                + [
                    MagicMock(returncode=0, stdout="", stderr=""),  # commit
                    MagicMock(returncode=0, stdout="", stderr=""),  # push
                ]
            )

            commands.commit_cmd()

            assert mock_run_safe.call_count == 3 + n + m
            # Commit call is at index 1 + n + m (after add + N resets + M agdt resets)
            commit_call_args = mock_run_safe.call_args_list[1 + n + m][0][0]
            assert "--amend" not in commit_call_args

    def test_commit_cmd_uses_template_message(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main
    ):
        """Test commit_cmd prefers the rendered template message over commit_message state."""
        state.set_value("commit_message", "State commit message")

        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        with (
            patch(
                "agentic_devtools.cli.git.commit_template.resolve_commit_message_from_template",
                return_value="Template commit message",
            ),
            patch("agentic_devtools.cli.git.commands.create_commit") as mock_create_commit,
        ):
            commands.commit_cmd()

        mock_create_commit.assert_called_once_with("Template commit message", False)

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
                "jira_issue_key": "PROJECT-1234",
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
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
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
                "jira_issue_key": "PROJECT-1234",
                "checklist": {
                    "items": [{"id": 1, "text": "Task 1", "completed": False}],
                    "modified_by_agent": False,
                },
            },
        )

        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * len(operations.STAGE_EXCLUDE_FILES)  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * len(AGDT_GITIGNORE_ENTRIES)  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        with patch.object(sys, "argv", ["agdt-git-save-work", "--completed", "1"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        assert "All checklist items complete" in captured.out

    def test_commit_cmd_dry_run_cli_flag(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --dry-run CLI flag triggers dry-run mode."""
        state.set_value("commit_message", "Test commit")

        with patch.object(sys, "argv", ["agdt-git-save-work", "--dry-run"]):
            commands.commit_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_commit_cmd_skip_stage_cli_flag(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --skip-stage CLI flag skips staging."""
        state.set_value("commit_message", "Test commit")

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        with patch.object(sys, "argv", ["agdt-git-save-work", "--skip-stage"]):
            commands.commit_cmd()

        assert mock_run_safe.call_count == 2
        captured = capsys.readouterr()
        assert "Skipping stage" in captured.out

    def test_commit_cmd_skip_push_cli_flag(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --skip-push CLI flag skips push."""
        state.set_value("commit_message", "Test commit")

        with patch.object(sys, "argv", ["agdt-git-save-work", "--skip-push"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        assert "Skipping push" in captured.out

    def test_commit_cmd_dry_run_cli_overrides_state(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --dry-run CLI flag works even when state is not set."""
        state.set_value("commit_message", "Test commit")
        # dry_run is NOT set in state, but CLI flag should take effect

        with patch.object(sys, "argv", ["agdt-git-save-work", "--dry-run"]):
            commands.commit_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_commit_cmd_skip_stage_cli_overrides_state(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --skip-stage CLI flag works even when state is not set."""
        state.set_value("commit_message", "Test commit")
        # skip_stage is NOT set in state, but CLI flag should take effect

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        with patch.object(sys, "argv", ["agdt-git-save-work", "--skip-stage"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        assert "Skipping stage" in captured.out

    def test_commit_cmd_all_flags_combined(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --dry-run --skip-stage --skip-push all work together."""
        state.set_value("commit_message", "Test commit")

        with patch.object(sys, "argv", ["agdt-git-save-work", "--dry-run", "--skip-stage", "--skip-push"]):
            commands.commit_cmd()

        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Skipping stage" in captured.out
        assert "Skipping push" in captured.out

    def test_persist_commit_message_called_with_dry_run_false(
        self,
        temp_state_dir,
        clear_state_before,
        mock_run_safe,
        mock_should_amend,
        mock_sync_with_main,
        mock_persist_commit_message,
    ):
        """Test _persist_effective_commit_message is called with dry_run=False after commit."""
        state.set_value("commit_message", "Test commit")

        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        commands.commit_cmd()

        mock_persist_commit_message.assert_called_once_with(False)

    def test_persist_commit_message_called_with_dry_run_true(
        self,
        temp_state_dir,
        clear_state_before,
        mock_run_safe,
        mock_should_amend,
        mock_sync_with_main,
        mock_persist_commit_message,
    ):
        """Test _persist_effective_commit_message is called with dry_run=True in dry-run mode."""
        state.set_value("commit_message", "Test commit")
        state.set_value("dry_run", True)

        commands.commit_cmd()

        mock_persist_commit_message.assert_called_once_with(True)

    def test_commit_cmd_empty_cli_commit_message_does_not_fallback(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main
    ):
        """Test explicit empty --commit-message is passed through without template/state fallback."""
        state.set_value("commit_message", "State commit message")

        with (
            patch.object(sys, "argv", ["agdt-git-save-work", "--commit-message", ""]),
            patch(
                "agentic_devtools.cli.git.commit_template.resolve_commit_message_from_template",
                return_value="Template commit message",
            ) as mock_template,
            patch("agentic_devtools.cli.git.commands.resolve_commit_intent", side_effect=SystemExit(1)) as mock_resolve,
            pytest.raises(SystemExit) as exc_info,
        ):
            commands.commit_cmd()

        assert exc_info.value.code == 1
        mock_template.assert_not_called()
        assert mock_resolve.call_args.kwargs["cli_commit_message"] == ""
        mock_run_safe.assert_not_called()


class TestCommitCmdNewTitleParams:
    """Tests for --commit-message-title and --overwrite-commit-message-title CLI flags."""

    def test_commit_message_title_creates_new_commit(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --commit-message-title creates a new commit when no commits ahead."""
        mock_should_amend.return_value = False
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        with patch.object(sys, "argv", ["cmd", "--commit-message-title", "feat: new feature"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        assert "Creating new commit" in captured.out

    def test_commit_message_title_rejects_when_commits_ahead(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --commit-message-title errors if branch has commits ahead."""
        mock_should_amend.return_value = True
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
        )

        with patch.object(sys, "argv", ["cmd", "--commit-message-title", "feat: new feature"]):
            try:
                commands.commit_cmd()
                assert False, "Should have exited"
            except SystemExit as e:
                assert e.code == 1

        captured = capsys.readouterr()
        assert "--commit-message-title is for new commits" in captured.err
        assert "--overwrite-commit-message-title (or overwrite_commit_message_title state key)" in captured.err

    def test_overwrite_commit_message_title_amends(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --overwrite-commit-message-title amends with preserved body."""
        mock_should_amend.return_value = True
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            # git log is called BEFORE stage_changes (to extract existing body)
            [MagicMock(returncode=0, stdout="old title\n\nexisting body", stderr="")]  # git log
            + [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # amend
                MagicMock(returncode=0, stdout="", stderr=""),  # force push
            ]
        )

        with patch.object(sys, "argv", ["cmd", "--overwrite-commit-message-title", "feat: new title"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        assert "will amend" in captured.out
        assert "--- Commit Title Change ---" in captured.out

    def test_overwrite_commit_message_title_rejects_when_no_commits_ahead(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test --overwrite-commit-message-title errors if no commits ahead."""
        mock_should_amend.return_value = False
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
        )

        with patch.object(sys, "argv", ["cmd", "--overwrite-commit-message-title", "feat: new"]):
            try:
                commands.commit_cmd()
                assert False, "Should have exited"
            except SystemExit as e:
                assert e.code == 1

        captured = capsys.readouterr()
        assert "--overwrite-commit-message-title requires an existing commit" in captured.err
        assert "--commit-message-title (or commit_message_title state key)" in captured.err

    def test_overwrite_commit_message_title_rejects_commit_message_argument(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test overwrite mode rejects --commit-message to avoid silent body ignore."""
        with patch.object(
            sys, "argv", ["cmd", "--overwrite-commit-message-title", "feat: new title", "--commit-message", "body"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                commands.commit_cmd()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Cannot combine --overwrite-commit-message-title with --commit-message" in captured.err

    def test_overwrite_commit_message_title_skips_template_resolution(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main
    ):
        """Test CLI overwrite mode does not resolve the commit template."""
        state.set_value("dry_run", True)
        mock_should_amend.return_value = True

        with (
            patch.object(sys, "argv", ["cmd", "--overwrite-commit-message-title", "feat: new title"]),
            patch(
                "agentic_devtools.cli.git.commit_template.resolve_commit_message_from_template",
                side_effect=AssertionError("template resolution should be skipped"),
            ),
            patch(
                "agentic_devtools.cli.git.commands.run_git",
                return_value=MagicMock(stdout="old title\n\nbody", stderr=""),
            ),
            patch("agentic_devtools.cli.git.commands.amend_commit") as mock_amend_commit,
        ):
            commands.commit_cmd()

        mock_amend_commit.assert_called_once_with("feat: new title\n\nbody", True, old_title="old title")

    def test_both_title_params_conflict_exits(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test error when both title params are specified."""
        state.set_value("commit_message_title", "from state")
        state.set_value("overwrite_commit_message_title", "also from state")

        try:
            commands.commit_cmd()
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 1

        captured = capsys.readouterr()
        assert "Cannot use both" in captured.err

    def test_legacy_path_still_works(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test that plain commit_message still works (legacy path)."""
        state.set_value("commit_message", "legacy: full message")
        mock_should_amend.return_value = False
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        commands.commit_cmd()

        captured = capsys.readouterr()
        assert "Creating new commit" in captured.out

    def test_state_key_commit_message_title(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test commit_message_title state key triggers create path."""
        state.set_value("commit_message_title", "feat: from state key")
        mock_should_amend.return_value = False
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]
        )

        commands.commit_cmd()

        captured = capsys.readouterr()
        assert "Creating new commit" in captured.out

    def test_state_key_commit_message_title_error_mentions_state_key(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test create-path branch-state errors name the state key when state drove the intent."""
        state.set_value("commit_message_title", "feat: from state key")
        mock_should_amend.return_value = True

        with pytest.raises(SystemExit) as exc_info:
            commands.commit_cmd()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "commit_message_title state key is for new commits" in captured.err
        assert "--overwrite-commit-message-title (or overwrite_commit_message_title state key)" in captured.err

    def test_state_key_overwrite_commit_message_title(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test overwrite_commit_message_title state key triggers overwrite path."""
        state.set_value("overwrite_commit_message_title", "feat: overwrite from state")
        mock_should_amend.return_value = True
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="old title\n\nbody text", stderr="")]  # git log
            + [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # amend
                MagicMock(returncode=0, stdout="", stderr=""),  # force push
            ]
        )

        commands.commit_cmd()

        captured = capsys.readouterr()
        assert "will amend" in captured.out

    def test_state_key_overwrite_commit_message_title_error_mentions_state_key(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test overwrite-path branch-state errors name the state key when state drove the intent."""
        state.set_value("overwrite_commit_message_title", "feat: overwrite from state")
        mock_should_amend.return_value = False

        with pytest.raises(SystemExit) as exc_info:
            commands.commit_cmd()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "overwrite_commit_message_title state key requires an existing commit" in captured.err
        assert "--commit-message-title (or commit_message_title state key)" in captured.err

    def test_state_key_overwrite_commit_message_title_skips_template_resolution(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main
    ):
        """Test state-driven overwrite mode does not resolve the commit template."""
        state.set_value("overwrite_commit_message_title", "feat: overwrite from state")
        state.set_value("dry_run", True)
        mock_should_amend.return_value = True

        with (
            patch(
                "agentic_devtools.cli.git.commit_template.resolve_commit_message_from_template",
                side_effect=AssertionError("template resolution should be skipped"),
            ),
            patch(
                "agentic_devtools.cli.git.commands.run_git",
                return_value=MagicMock(stdout="old title\n\nbody", stderr=""),
            ),
            patch("agentic_devtools.cli.git.commands.amend_commit") as mock_amend_commit,
        ):
            commands.commit_cmd()

        mock_amend_commit.assert_called_once_with("feat: overwrite from state\n\nbody", True, old_title="old title")

    def test_overwrite_commit_message_title_no_body(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test overwrite when existing commit has no body."""
        state.set_value("overwrite_commit_message_title", "feat: new title")
        mock_should_amend.return_value = True
        n = len(operations.STAGE_EXCLUDE_FILES)
        m = len(AGDT_GITIGNORE_ENTRIES)
        mock_run_safe.side_effect = (
            [MagicMock(returncode=0, stdout="old title only", stderr="")]  # git log
            + [MagicMock(returncode=0, stdout="", stderr="")]  # add
            + [MagicMock(returncode=0, stdout="", stderr="")] * n  # resets
            + [MagicMock(returncode=0, stdout="", stderr="")] * m  # agdt entry resets
            + [
                MagicMock(returncode=0, stdout="", stderr=""),  # amend
                MagicMock(returncode=0, stdout="", stderr=""),  # force push
            ]
        )

        commands.commit_cmd()

        captured = capsys.readouterr()
        assert "will amend" in captured.out

    def test_commit_message_title_state_value_is_stringified(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main
    ):
        """Test non-string title state values are coerced to strings."""
        state.set_value("commit_message_title", 123)
        state.set_value("commit_message", "body text")
        state.set_value("dry_run", True)
        mock_should_amend.return_value = False

        with patch("agentic_devtools.cli.git.commands.create_commit") as mock_create_commit:
            commands.commit_cmd()

        mock_create_commit.assert_called_once_with("123\n\nbody text", True)

    def test_overwrite_commit_message_title_preserves_existing_body_verbatim(
        self, temp_state_dir, clear_state_before, mock_should_amend, mock_sync_with_main
    ):
        """Test overwrite path preserves existing body formatting exactly."""
        state.set_value("overwrite_commit_message_title", "feat: new title")
        state.set_value("dry_run", True)
        mock_should_amend.return_value = True

        with (
            patch(
                "agentic_devtools.cli.git.commands.run_git",
                return_value=MagicMock(
                    stdout="old title\n\n  body line  \n\ntrailer: keep  \n",
                    stderr="",
                ),
            ),
            patch("agentic_devtools.cli.git.commands.amend_commit") as mock_amend_commit,
        ):
            commands.commit_cmd()

        mock_amend_commit.assert_called_once_with(
            "feat: new title\n\n  body line  \n\ntrailer: keep  ",
            True,
            old_title="old title",
        )
