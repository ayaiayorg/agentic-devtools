"""
Tests for git CLI commands (dfly-git-save-work, dfly-git-amend, etc.).

Tests cover:
- commit_cmd workflow (dfly-git-save-work)
- amend_cmd workflow (dfly-git-amend)
- stage_cmd, push_cmd, force_push_cmd, publish_cmd
- State flags (skip_stage, skip_push, skip_rebase, dry_run)
"""

from unittest.mock import MagicMock, patch

import pytest

from dfly_ai_helpers import state
from dfly_ai_helpers.cli.git import commands, core

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


@pytest.fixture
def mock_run_safe():
    """Mock subprocess.run for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def mock_should_amend():
    """Mock should_amend_instead_of_commit to always return False (new commit)."""
    with patch("dfly_ai_helpers.cli.git.commands.should_amend_instead_of_commit") as mock:
        mock.return_value = False
        yield mock


@pytest.fixture
def mock_sync_with_main():
    """Mock _sync_with_main to skip fetch/rebase for simpler testing.

    Returns False by default (no rebase occurred), meaning the push type
    depends on should_amend. Set return_value=True to simulate a rebase.
    """
    with patch("dfly_ai_helpers.cli.git.commands._sync_with_main") as mock:
        mock.return_value = False  # No rebase occurred by default
        yield mock


# =============================================================================
# Commit Command Tests
# =============================================================================


class TestCommitCommand:
    """Tests for dfly-git-save-work command."""

    def test_commit_cmd_full_workflow(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main
    ):
        """Test full commit workflow (with sync mocked)."""
        state.set_value("commit_message", "Test commit")

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        commands.commit_cmd()

        assert mock_run_safe.call_count == 4
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

        assert mock_run_safe.call_count == 2
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
        """Test that force push is used when rebase occurs, even for new commits.

        This is the belt-and-suspenders fix: if a rebase rewrites history,
        we must force push regardless of whether it was a new commit or amend.
        """
        state.set_value("commit_message", "Test commit")

        # Mock _sync_with_main to return True (rebase occurred)
        with patch("dfly_ai_helpers.cli.git.commands._sync_with_main", return_value=True):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # add
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="", stderr=""),  # force push
            ]

            commands.commit_cmd()

            # Should be 3 calls: add, commit, force_push (not 4 with branch lookup)
            assert mock_run_safe.call_count == 3
            captured = capsys.readouterr()
            assert "Force pushing" in captured.out


# =============================================================================
# Amend Command Tests
# =============================================================================


class TestAmendCommand:
    """Tests for dfly-git-amend command."""

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


# =============================================================================
# Simple Command Tests
# =============================================================================


class TestStageCommand:
    """Tests for dfly-git-stage command."""

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


class TestPushCommand:
    """Tests for dfly-git-push command."""

    def test_push_cmd(self, temp_state_dir, clear_state_before, mock_run_safe):
        """Test push command."""
        commands.push_cmd()
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "push"]

    def test_push_cmd_dry_run(self, temp_state_dir, clear_state_before, mock_run_safe, capsys):
        """Test push command dry run."""
        state.set_value("dry_run", True)
        commands.push_cmd()
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


class TestForcePushCommand:
    """Tests for dfly-git-force-push command."""

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


class TestPublishCommand:
    """Tests for dfly-git-publish command."""

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


# =============================================================================
# Smart Amend Detection Tests
# =============================================================================


class TestSmartCommitAmendDetection:
    """Tests for smart commit/amend detection."""

    def test_commit_uses_amend_when_should_amend(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_sync_with_main
    ):
        """Test that commit cmd uses amend when should_amend_instead_of_commit returns True."""
        state.set_value("commit_message", "Updated commit")
        state.set_value("jira.issue_key", "DFLY-1234")

        # Mock should_amend to return True
        with patch("dfly_ai_helpers.cli.git.commands.should_amend_instead_of_commit") as mock_should:
            mock_should.return_value = True
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # add
                MagicMock(returncode=0, stdout="", stderr=""),  # amend
                MagicMock(returncode=0, stdout="", stderr=""),  # force push
            ]

            commands.commit_cmd()

            # Verify amend flow was used (3 calls: stage, amend, force-push)
            assert mock_run_safe.call_count == 3
            # Check that the second call was amend (--amend flag)
            second_call_args = mock_run_safe.call_args_list[1][0][0]
            assert "--amend" in second_call_args

    def test_commit_uses_new_commit_when_should_not_amend(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_sync_with_main
    ):
        """Test that commit cmd uses new commit when should_amend returns False."""
        state.set_value("commit_message", "New commit")
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("dfly_ai_helpers.cli.git.commands.should_amend_instead_of_commit") as mock_should:
            mock_should.return_value = False
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # add
                MagicMock(returncode=0, stdout="", stderr=""),  # commit
                MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
                MagicMock(returncode=0, stdout="", stderr=""),  # push
            ]

            commands.commit_cmd()

            # Verify new commit flow was used (4 calls: stage, commit, branch, publish)
            assert mock_run_safe.call_count == 4
            # Check that the second call was commit (not amend)
            second_call_args = mock_run_safe.call_args_list[1][0][0]
            assert "--amend" not in second_call_args


# =============================================================================
# Completed Parameter Tests
# =============================================================================


class TestCommitCompletedParameter:
    """Tests for --completed parameter in commit command."""

    def test_commit_with_completed_marks_items(
        self, temp_state_dir, clear_state_before, mock_run_safe, mock_should_amend, mock_sync_with_main, capsys
    ):
        """Test that --completed parameter marks checklist items."""
        import sys
        from unittest.mock import patch as mock_patch

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

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        # Mock sys.argv to include --completed
        with mock_patch.object(sys, "argv", ["dfly-git-save-work", "--completed", "1,2"]):
            commands.commit_cmd()

        # Verify checklist was updated
        from dfly_ai_helpers.cli.workflows.checklist import get_checklist

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
        import sys
        from unittest.mock import patch as mock_patch

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

        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # add
            MagicMock(returncode=0, stdout="", stderr=""),  # commit
            MagicMock(returncode=0, stdout="feature/test\n", stderr=""),  # branch
            MagicMock(returncode=0, stdout="", stderr=""),  # push
        ]

        with mock_patch.object(sys, "argv", ["dfly-git-save-work", "--completed", "1"]):
            commands.commit_cmd()

        captured = capsys.readouterr()
        # Should mention implementation review since all items are now complete
        assert "All checklist items complete" in captured.out


class TestGetIssueKeyFromState:
    """Tests for _get_issue_key_from_state function."""

    def test_returns_none_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test returns None when no workflow is set."""
        result = commands._get_issue_key_from_state()
        assert result is None

    def test_returns_key_from_workflow_context(self, temp_state_dir, clear_state_before):
        """Test returns jira_issue_key from workflow context."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-5678"},
        )
        result = commands._get_issue_key_from_state()
        assert result == "DFLY-5678"

    def test_returns_none_when_workflow_has_no_context(self, temp_state_dir, clear_state_before):
        """Test returns None when workflow has no context."""
        state.set_value("workflow", {"name": "test", "status": "in-progress"})
        result = commands._get_issue_key_from_state()
        assert result is None


class TestMarkChecklistItemsCompleted:
    """Tests for _mark_checklist_items_completed function."""

    def test_does_nothing_when_empty_list(self, temp_state_dir, clear_state_before, capsys):
        """Test does nothing when item_ids is empty."""
        commands._mark_checklist_items_completed([])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_prints_warning_when_no_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test prints warning when no checklist exists."""
        commands._mark_checklist_items_completed([1, 2])
        captured = capsys.readouterr()
        assert "No checklist found" in captured.out

    def test_marks_items_in_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test marks items as completed in checklist."""
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

        commands._mark_checklist_items_completed([1])

        captured = capsys.readouterr()
        assert "Marked checklist items as completed" in captured.out


class TestTriggerImplementationReview:
    """Tests for _trigger_implementation_review function."""

    def test_triggers_workflow_event(self, temp_state_dir, clear_state_before):
        """Test triggers CHECKLIST_COMPLETE workflow event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        # Should not raise
        commands._trigger_implementation_review()

    def test_handles_no_workflow(self, temp_state_dir, clear_state_before):
        """Test handles case when no workflow is active."""
        # Should not raise
        commands._trigger_implementation_review()


class TestSyncWithMain:
    """Tests for _sync_with_main function.

    The function returns True if a rebase occurred (history rewritten),
    False if no rebase occurred (skipped, fetch failed, or no rebase needed).
    """

    def test_skips_rebase_when_flag_set(self, temp_state_dir, clear_state_before, capsys):
        """Test skips rebase when skip_rebase is True."""
        result = commands._sync_with_main(dry_run=False, skip_rebase=True)

        assert result is False  # No rebase occurred
        captured = capsys.readouterr()
        assert "Skipping rebase" in captured.out

    @patch("dfly_ai_helpers.cli.git.commands.fetch_main")
    def test_continues_on_fetch_failure(self, mock_fetch, temp_state_dir, clear_state_before, capsys):
        """Test continues when fetch from main fails."""
        mock_fetch.return_value = False

        result = commands._sync_with_main(dry_run=False, skip_rebase=False)

        assert result is False  # No rebase occurred
        captured = capsys.readouterr()
        assert "Could not fetch from origin/main" in captured.out

    @patch("dfly_ai_helpers.cli.git.commands.rebase_onto_main")
    @patch("dfly_ai_helpers.cli.git.commands.fetch_main")
    def test_handles_rebase_success(self, mock_fetch, mock_rebase, temp_state_dir, clear_state_before):
        """Test returns True on successful rebase (history was rewritten)."""
        mock_fetch.return_value = True
        mock_rebase.return_value = MagicMock(is_success=True, was_rebased=True)

        result = commands._sync_with_main(dry_run=False, skip_rebase=False)

        assert result is True  # Rebase occurred

    @patch("dfly_ai_helpers.cli.git.commands.rebase_onto_main")
    @patch("dfly_ai_helpers.cli.git.commands.fetch_main")
    def test_returns_false_when_no_rebase_needed(self, mock_fetch, mock_rebase, temp_state_dir, clear_state_before):
        """Test returns False when already up-to-date (no rebase needed)."""
        mock_fetch.return_value = True
        mock_rebase.return_value = MagicMock(is_success=True, was_rebased=False)

        result = commands._sync_with_main(dry_run=False, skip_rebase=False)

        assert result is False  # No rebase occurred
