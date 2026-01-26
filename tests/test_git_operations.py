"""
Tests for git operations.

Tests cover:
- Staging changes
- Creating commits
- Amending commits
- Publishing branches
- Pushing (regular and force)
"""

from unittest.mock import MagicMock, patch

import pytest

from dfly_ai_helpers.cli.git import core, operations

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_run_safe():
    """Mock subprocess.run for git commands."""
    with patch.object(core, "run_safe") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run


# =============================================================================
# Staging Tests
# =============================================================================


class TestStageChanges:
    """Tests for staging changes."""

    def test_stage_changes(self, mock_run_safe):
        """Test staging all changes."""
        operations.stage_changes(dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "add", "."]

    def test_stage_changes_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.stage_changes(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# =============================================================================
# Commit Tests
# =============================================================================


class TestCreateCommit:
    """Tests for commit creation."""

    def test_create_commit(self, mock_run_safe):
        """Test creating a commit uses temp file for message."""
        operations.create_commit("Test message", dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        # Now uses -F with temp file for consistent multiline handling
        assert cmd[0:3] == ["git", "commit", "-F"]
        assert len(cmd) == 4  # git commit -F <temp_file>

    def test_create_commit_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows message."""
        operations.create_commit("Test message", dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test message" in captured.out

    def test_create_commit_multiline(self, mock_run_safe):
        """Test multiline commit message uses temp file."""
        message = "Title\n\n- Change 1\n- Change 2"
        operations.create_commit(message, dry_run=False)
        cmd = mock_run_safe.call_args[0][0]
        # Now uses temp file for all messages
        assert cmd[0:2] == ["git", "commit"]
        assert "-F" in cmd


class TestAmendCommit:
    """Tests for commit amendment."""

    def test_amend_commit_uses_temp_file(self, mock_run_safe):
        """Test amending a commit uses temp file with -F flag."""
        operations.amend_commit("Test message", dry_run=False)

        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd[0:3] == ["git", "commit", "--amend"]
        assert "-F" in cmd

    def test_amend_commit_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows message."""
        operations.amend_commit("Test message", dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Test message" in captured.out


# =============================================================================
# Push Tests
# =============================================================================


class TestPublishBranch:
    """Tests for branch publishing."""

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


class TestForcePush:
    """Tests for force push."""

    def test_force_push(self, mock_run_safe):
        """Test force push with lease."""
        operations.force_push(dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "push", "--force-with-lease"]

    def test_force_push_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.force_push(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


class TestPush:
    """Tests for regular push."""

    def test_push(self, mock_run_safe):
        """Test regular push."""
        operations.push(dry_run=False)
        mock_run_safe.assert_called_once()
        cmd = mock_run_safe.call_args[0][0]
        assert cmd == ["git", "push"]

    def test_push_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute."""
        operations.push(dry_run=True)
        mock_run_safe.assert_not_called()
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# =============================================================================
# Smart Amend Detection Tests
# =============================================================================


class TestShouldAmendInsteadOfCommit:
    """Tests for should_amend_instead_of_commit function.

    The function now follows a simple rule: amend if there are commits ahead of main.
    The issue_key parameter is kept for API compatibility but no longer affects the decision.
    """

    def test_returns_false_when_no_commits_ahead(self, mock_run_safe):
        """Test returns False when branch has no commits ahead of main."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=False):
            result = operations.should_amend_instead_of_commit("DFLY-1234")
            assert result is False

    def test_returns_true_when_commits_ahead_with_issue_key(self, mock_run_safe):
        """Test returns True when commits ahead, regardless of issue key match."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=True):
            # Issue key is no longer checked - we always amend if commits ahead
            result = operations.should_amend_instead_of_commit("DFLY-1234")
            assert result is True

    def test_returns_true_when_commits_ahead_with_different_issue_key(self, mock_run_safe):
        """Test returns True even when issue key doesn't match last commit.

        This is the key change from the old behavior - we now amend regardless
        of whether the issue key matches, enforcing single-commit-per-feature.
        """
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=True):
            # Even with a different issue key, we amend (single-commit policy)
            result = operations.should_amend_instead_of_commit("DIFFERENT-KEY")
            assert result is True

    def test_returns_true_when_no_issue_key_and_commits_ahead(self, mock_run_safe):
        """Test returns True when no issue key provided but commits ahead."""
        with patch.object(operations, "branch_has_commits_ahead_of_main", return_value=True):
            result = operations.should_amend_instead_of_commit(None)
            assert result is True


class TestLastCommitContainsIssueKey:
    """Tests for last_commit_contains_issue_key function."""

    def test_returns_true_when_key_found(self, mock_run_safe):
        """Test returns True when issue key is in commit message."""
        mock_run_safe.return_value = MagicMock(
            returncode=0, stdout="feature(DFLY-1234): implement feature\n", stderr=""
        )

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is True

    def test_returns_true_case_insensitive(self, mock_run_safe):
        """Test matching is case-insensitive."""
        mock_run_safe.return_value = MagicMock(
            returncode=0, stdout="feature(dfly-1234): implement feature\n", stderr=""
        )

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is True

    def test_returns_false_when_key_not_found(self, mock_run_safe):
        """Test returns False when issue key is not in commit message."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="feature(DFLY-5678): different issue\n", stderr="")

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is False

    def test_returns_false_on_error(self, mock_run_safe):
        """Test returns False on git command error."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        result = operations.last_commit_contains_issue_key("DFLY-1234")

        assert result is False


# =============================================================================
# Local Branch Matches Origin Tests
# =============================================================================


class TestLocalBranchMatchesOrigin:
    """Tests for local_branch_matches_origin function."""

    def test_returns_true_when_in_sync(self, mock_run_safe):
        """Test returns True when local and origin are in sync."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse origin/branch
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits ahead
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits behind
            ]
            result = operations.local_branch_matches_origin()
            assert result is True

    def test_returns_false_when_ahead(self, mock_run_safe):
        """Test returns False when local is ahead of origin."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="2\n", stderr=""),  # 2 commits ahead
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits behind
            ]
            result = operations.local_branch_matches_origin()
            assert result is False

    def test_returns_false_when_behind(self, mock_run_safe):
        """Test returns False when local is behind origin."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits ahead
                MagicMock(returncode=0, stdout="3\n", stderr=""),  # 3 commits behind
            ]
            result = operations.local_branch_matches_origin()
            assert result is False

    def test_returns_false_when_origin_branch_not_exists(self, mock_run_safe):
        """Test returns False when origin branch doesn't exist."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
            result = operations.local_branch_matches_origin()
            assert result is False

    def test_returns_false_on_invalid_value(self, mock_run_safe):
        """Test returns False when git returns invalid value."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="invalid\n", stderr=""),  # invalid
            ]
            result = operations.local_branch_matches_origin()
            assert result is False

    def test_returns_false_on_behind_error(self, mock_run_safe):
        """Test returns False when checking behind commits fails."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits ahead
                MagicMock(returncode=1, stdout="", stderr="error"),  # behind check fails
            ]
            result = operations.local_branch_matches_origin()
            assert result is False

    def test_returns_false_on_behind_invalid_value(self, mock_run_safe):
        """Test returns False when behind returns invalid value."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits ahead
                MagicMock(returncode=0, stdout="not-a-number\n", stderr=""),  # invalid
            ]
            result = operations.local_branch_matches_origin()
            assert result is False


# =============================================================================
# Branch Has Commits Ahead of Main Tests
# =============================================================================


class TestBranchHasCommitsAheadOfMain:
    """Tests for branch_has_commits_ahead_of_main function."""

    def test_returns_true_when_ahead(self, mock_run_safe):
        """Test returns True when branch is ahead of main."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse origin/main
                MagicMock(returncode=0, stdout="3\n", stderr=""),  # 3 commits ahead
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is True

    def test_returns_false_when_not_ahead(self, mock_run_safe):
        """Test returns False when branch is not ahead."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse origin/main
                MagicMock(returncode=0, stdout="0\n", stderr=""),  # 0 commits ahead
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_returns_false_when_on_main(self, mock_run_safe):
        """Test returns False when already on main branch."""
        with patch.object(operations, "get_current_branch", return_value="main"):
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_fallback_to_main_without_origin(self, mock_run_safe):
        """Test falls back to main when origin/main doesn't exist."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="not found"),  # origin/main fails
                MagicMock(returncode=0, stdout="", stderr=""),  # main succeeds
                MagicMock(returncode=0, stdout="2\n", stderr=""),  # 2 commits ahead
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is True

    def test_returns_false_when_main_not_found(self, mock_run_safe):
        """Test returns False when neither origin/main nor main exists."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="not found"),  # origin/main fails
                MagicMock(returncode=1, stdout="", stderr="not found"),  # main also fails
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_returns_false_on_rev_list_error(self, mock_run_safe):
        """Test returns False when rev-list fails."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=1, stdout="", stderr="error"),  # rev-list fails
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False

    def test_returns_false_on_invalid_count(self, mock_run_safe):
        """Test returns False when count is not a valid integer."""
        with patch.object(operations, "get_current_branch", return_value="feature/test"):
            mock_run_safe.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # rev-parse succeeds
                MagicMock(returncode=0, stdout="invalid\n", stderr=""),  # invalid count
            ]
            result = operations.branch_has_commits_ahead_of_main()
            assert result is False


# =============================================================================
# Has Local Changes Tests
# =============================================================================


class TestHasLocalChanges:
    """Tests for has_local_changes function."""

    def test_returns_true_with_staged_changes(self, mock_run_safe):
        """Test returns True when there are staged changes."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="")  # diff --cached shows changes
        result = operations.has_local_changes()
        assert result is True

    def test_returns_true_with_unstaged_changes(self, mock_run_safe):
        """Test returns True when there are unstaged changes."""
        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # diff --cached OK (no staged)
            MagicMock(returncode=1, stdout="", stderr=""),  # diff shows unstaged changes
        ]
        result = operations.has_local_changes()
        assert result is True

    def test_returns_true_with_untracked_files(self, mock_run_safe):
        """Test returns True when there are untracked files."""
        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # diff --cached OK
            MagicMock(returncode=0, stdout="", stderr=""),  # diff OK
            MagicMock(returncode=0, stdout="untracked.txt\n", stderr=""),  # has untracked
        ]
        result = operations.has_local_changes()
        assert result is True

    def test_returns_false_with_no_changes(self, mock_run_safe):
        """Test returns False when there are no changes."""
        mock_run_safe.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # diff --cached OK
            MagicMock(returncode=0, stdout="", stderr=""),  # diff OK
            MagicMock(returncode=0, stdout="", stderr=""),  # no untracked files
        ]
        result = operations.has_local_changes()
        assert result is False


# =============================================================================
# Get Commits Behind Main Tests
# =============================================================================


class TestGetCommitsBehindMain:
    """Tests for get_commits_behind_main function."""

    def test_returns_count_when_behind(self, mock_run_safe):
        """Test returns correct count when behind main."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="5\n", stderr="")
        result = operations.get_commits_behind_main()
        assert result == 5

    def test_returns_zero_when_up_to_date(self, mock_run_safe):
        """Test returns 0 when up to date with main."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="0\n", stderr="")
        result = operations.get_commits_behind_main()
        assert result == 0

    def test_returns_zero_on_error(self, mock_run_safe):
        """Test returns 0 when git command fails."""
        mock_run_safe.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = operations.get_commits_behind_main()
        assert result == 0

    def test_returns_zero_on_invalid_count(self, mock_run_safe):
        """Test returns 0 when count is not a valid integer."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="invalid\n", stderr="")
        result = operations.get_commits_behind_main()
        assert result == 0


# =============================================================================
# Fetch Main Tests
# =============================================================================


class TestFetchMain:
    """Tests for fetch_main function."""

    def test_fetch_success(self, mock_run_safe):
        """Test successful fetch."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = operations.fetch_main(dry_run=False)
            assert result is True

    def test_fetch_failure(self, mock_run_safe):
        """Test fetch failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = operations.fetch_main(dry_run=False)
            assert result is False

    def test_fetch_dry_run(self, mock_run_safe, capsys):
        """Test fetch dry run."""
        result = operations.fetch_main(dry_run=True)
        assert result is True
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# =============================================================================
# Rebase Onto Main Tests
# =============================================================================


class TestRebaseResult:
    """Tests for RebaseResult class."""

    def test_success_result(self):
        """Test SUCCESS result properties."""
        result = operations.RebaseResult(operations.RebaseResult.SUCCESS)
        assert result.status == operations.RebaseResult.SUCCESS
        assert result.is_success
        assert result.was_rebased  # SUCCESS means rebase actually occurred
        assert not result.needs_manual_resolution

    def test_no_rebase_needed_result(self):
        """Test NO_REBASE_NEEDED result properties."""
        result = operations.RebaseResult(operations.RebaseResult.NO_REBASE_NEEDED)
        assert result.status == operations.RebaseResult.NO_REBASE_NEEDED
        assert result.is_success
        assert not result.was_rebased  # NO_REBASE_NEEDED means no history rewrite
        assert not result.needs_manual_resolution

    def test_conflict_result(self):
        """Test CONFLICT result properties."""
        result = operations.RebaseResult(operations.RebaseResult.CONFLICT, "conflicts found")
        assert result.status == operations.RebaseResult.CONFLICT
        assert not result.is_success
        assert not result.was_rebased  # Conflict means rebase was aborted
        assert result.needs_manual_resolution
        assert "conflicts" in result.message

    def test_error_result(self):
        """Test ERROR result properties."""
        result = operations.RebaseResult(operations.RebaseResult.ERROR, "something broke")
        assert result.status == operations.RebaseResult.ERROR
        assert not result.is_success
        assert not result.was_rebased  # Error means rebase failed
        assert not result.needs_manual_resolution


class TestRebaseOntoMain:
    """Tests for rebase_onto_main function."""

    def test_no_rebase_needed(self, mock_run_safe):
        """Test returns NO_REBASE_NEEDED when already up to date."""
        with patch.object(operations, "get_commits_behind_main", return_value=0):
            result = operations.rebase_onto_main(dry_run=False)
            assert result.status == operations.RebaseResult.NO_REBASE_NEEDED
            assert result.is_success

    def test_dry_run(self, mock_run_safe, capsys):
        """Test dry run shows what would happen."""
        with patch.object(operations, "get_commits_behind_main", return_value=5):
            result = operations.rebase_onto_main(dry_run=True)
            assert result.is_success
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "5 commits behind" in captured.out

    def test_rebase_success(self, mock_run_safe):
        """Test successful rebase."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.SUCCESS
                assert result.is_success

    def test_rebase_conflict(self, mock_run_safe):
        """Test rebase with conflicts."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.side_effect = [
                    MagicMock(returncode=1, stdout="", stderr="CONFLICT"),  # rebase fails
                    MagicMock(returncode=0, stdout="", stderr=""),  # abort succeeds
                ]
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.CONFLICT
                assert result.needs_manual_resolution

    def test_rebase_conflict_abort_fails(self, mock_run_safe):
        """Test rebase conflict when abort also fails."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.side_effect = [
                    MagicMock(returncode=1, stdout="conflict", stderr=""),  # rebase fails
                    MagicMock(returncode=1, stdout="", stderr="abort failed"),  # abort fails
                ]
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.ERROR
                assert "abort" in result.message.lower()

    def test_rebase_other_error(self, mock_run_safe):
        """Test rebase with non-conflict error."""
        with patch.object(operations, "get_commits_behind_main", return_value=3):
            with patch.object(operations, "run_git") as mock_run_git:
                mock_run_git.side_effect = [
                    MagicMock(returncode=1, stdout="", stderr="some other error"),
                    MagicMock(returncode=0, stdout="", stderr=""),  # abort succeeds
                ]
                result = operations.rebase_onto_main(dry_run=False)
                assert result.status == operations.RebaseResult.ERROR


# =============================================================================
# Checkout Tests
# =============================================================================


class TestCheckoutResult:
    """Tests for CheckoutResult class."""

    def test_success_result(self):
        """Test SUCCESS result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.SUCCESS)
        assert result.status == operations.CheckoutResult.SUCCESS
        assert result.is_success
        assert not result.needs_user_action
        assert result.message == ""

    def test_uncommitted_changes_result(self):
        """Test UNCOMMITTED_CHANGES result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.UNCOMMITTED_CHANGES, "uncommitted changes message")
        assert result.status == operations.CheckoutResult.UNCOMMITTED_CHANGES
        assert not result.is_success
        assert result.needs_user_action
        assert "uncommitted" in result.message.lower()

    def test_branch_not_found_result(self):
        """Test BRANCH_NOT_FOUND result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.BRANCH_NOT_FOUND, "Branch feature/test not found")
        assert result.status == operations.CheckoutResult.BRANCH_NOT_FOUND
        assert not result.is_success
        assert result.needs_user_action
        assert "feature/test" in result.message

    def test_error_result(self):
        """Test ERROR result properties."""
        result = operations.CheckoutResult(operations.CheckoutResult.ERROR, "Something went wrong")
        assert result.status == operations.CheckoutResult.ERROR
        assert not result.is_success
        # ERROR doesn't need user action (unlike UNCOMMITTED_CHANGES and BRANCH_NOT_FOUND)
        assert not result.needs_user_action
        assert "Something went wrong" in result.message


class TestCheckoutBranch:
    """Tests for checkout_branch function."""

    def test_checkout_success(self, mock_run_safe):
        """Test successful checkout."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

                    result = operations.checkout_branch("feature/test", dry_run=False)

                    assert result.is_success
                    mock_run_git.assert_called()

    def test_checkout_already_on_branch(self, mock_run_safe):
        """Test checkout when already on the branch."""
        with patch.object(core, "get_current_branch", return_value="feature/test"):
            result = operations.checkout_branch("feature/test", dry_run=False)

            assert result.is_success

    def test_checkout_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute checkout."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            result = operations.checkout_branch("feature/test", dry_run=True)

            assert result.is_success
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "feature/test" in captured.out

    def test_checkout_uncommitted_changes(self, mock_run_safe):
        """Test checkout fails with uncommitted changes."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=True):
                result = operations.checkout_branch("feature/test", dry_run=False)

                assert not result.is_success
                assert result.status == operations.CheckoutResult.UNCOMMITTED_CHANGES

    def test_checkout_branch_not_found(self, mock_run_safe):
        """Test checkout fails when branch doesn't exist."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(
                        returncode=1,
                        stdout="",
                        stderr="error: pathspec 'feature/nonexistent' did not match any file(s) known to git",
                    )

                    result = operations.checkout_branch("feature/nonexistent", dry_run=False)

                    assert not result.is_success
                    assert result.status == operations.CheckoutResult.BRANCH_NOT_FOUND

    def test_checkout_generic_error(self, mock_run_safe):
        """Test checkout handles generic errors."""
        with patch.object(core, "get_current_branch", return_value="other-branch"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(
                        returncode=1,
                        stdout="",
                        stderr="fatal: some unexpected error",
                    )

                    result = operations.checkout_branch("feature/test", dry_run=False)

                    assert not result.is_success
                    assert result.status == operations.CheckoutResult.ERROR

    def test_checkout_from_detached_head(self, mock_run_safe):
        """Test checkout when starting from detached HEAD (get_current_branch raises SystemExit)."""
        with patch.object(core, "get_current_branch", side_effect=SystemExit(1)):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

                    result = operations.checkout_branch("feature/test", dry_run=False)

                    # Should still succeed since we catch SystemExit and proceed
                    assert result.is_success
                    mock_run_git.assert_called()

    def test_checkout_from_origin_when_local_does_not_exist(self, mock_run_safe):
        """Test checkout creates local branch from origin when local doesn't exist."""
        with patch.object(core, "get_current_branch", return_value="main"):
            with patch.object(operations, "has_local_changes", return_value=False):
                with patch.object(operations, "run_git") as mock_run_git:
                    # First call (checkout branch_name) fails, second (checkout -b from origin) succeeds
                    mock_run_git.side_effect = [
                        MagicMock(returncode=1, stdout="", stderr="did not match"),  # local fails
                        MagicMock(returncode=0, stdout="", stderr=""),  # from origin succeeds
                    ]

                    result = operations.checkout_branch("feature/new-branch", dry_run=False)

                    assert result.is_success
                    # Should have tried twice
                    assert mock_run_git.call_count == 2


# =============================================================================
# Get Files Changed on Branch Tests
# =============================================================================


class TestGetFilesChangedOnBranch:
    """Tests for get_files_changed_on_branch function."""

    def test_returns_files_when_branch_has_changes(self, mock_run_safe):
        """Test returns list of files when branch has changes."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(
                returncode=0,
                stdout="src/file1.ts\nsrc/file2.ts\nREADME.md\n",
                stderr="",
            )

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert len(result) == 3
            assert "src/file1.ts" in result
            assert "src/file2.ts" in result
            assert "README.md" in result

    def test_returns_empty_list_when_no_changes(self, mock_run_safe):
        """Test returns empty list when branch has no changes."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert len(result) == 0

    def test_falls_back_to_main_if_origin_main_not_found(self, mock_run_safe):
        """Test falls back to 'main' if 'origin/main' doesn't exist."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="error"),  # origin/main fails
                MagicMock(returncode=0, stdout="file.ts\n", stderr=""),  # main works
            ]

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert "file.ts" in result

    def test_returns_empty_list_on_error(self, mock_run_safe):
        """Test returns empty list on git command error."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr="error"),  # origin/main fails
                MagicMock(returncode=1, stdout="", stderr="error"),  # main fails
            ]

            result = operations.get_files_changed_on_branch()

            assert isinstance(result, list)
            assert len(result) == 0

    def test_uses_custom_main_branch(self, mock_run_safe):
        """Test uses custom main branch name."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="file.ts\n", stderr="")

            result = operations.get_files_changed_on_branch(main_branch="develop")

            assert "file.ts" in result
            # Check that origin/develop was used
            first_call = mock_run_git.call_args_list[0][0]
            assert "origin/develop...HEAD" in first_call


# =============================================================================
# Branch Safety Check Tests
# =============================================================================


class TestBranchSafetyCheckResult:
    """Tests for BranchSafetyCheckResult enum values."""

    def test_result_values_exist(self):
        """Test that all expected result values are defined."""
        assert operations.BranchSafetyCheckResult.SAFE == "safe"
        assert operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES == "uncommitted_changes"
        assert operations.BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN == "diverged_from_origin"
        assert operations.BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN == "branch_not_on_origin"
        assert operations.BranchSafetyCheckResult.NOT_ON_BRANCH == "not_on_branch"

    def test_result_is_safe_property(self):
        """Test is_safe property for different result states."""
        safe_result = operations.BranchSafetyCheckResult(operations.BranchSafetyCheckResult.SAFE, "Safe", "test")
        uncommitted_result = operations.BranchSafetyCheckResult(
            operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES, "Uncommitted", "test"
        )
        assert safe_result.is_safe is True
        assert uncommitted_result.is_safe is False

    def test_has_local_work_at_risk_property(self):
        """Test has_local_work_at_risk property for different result states."""
        uncommitted_result = operations.BranchSafetyCheckResult(
            operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES, "Uncommitted", "test"
        )
        diverged_result = operations.BranchSafetyCheckResult(
            operations.BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN, "Diverged", "test"
        )
        safe_result = operations.BranchSafetyCheckResult(operations.BranchSafetyCheckResult.SAFE, "Safe", "test")
        assert uncommitted_result.has_local_work_at_risk is True
        assert diverged_result.has_local_work_at_risk is True
        assert safe_result.has_local_work_at_risk is False


class TestCheckBranchSafeToRecreate:
    """Tests for check_branch_safe_to_recreate function."""

    def test_returns_safe_when_branch_does_not_exist_but_on_origin(self, mock_run_safe):
        """Test returns SAFE when branch doesn't exist locally but exists on origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr=""),  # branch doesn't exist locally
                MagicMock(returncode=0, stdout="abc123", stderr=""),  # origin/branch exists
            ]
            result = operations.check_branch_safe_to_recreate("feature/test")
            assert result.status == operations.BranchSafetyCheckResult.SAFE
            assert result.is_safe

    def test_returns_branch_not_on_origin_when_neither_exists(self, mock_run_safe):
        """Test returns BRANCH_NOT_ON_ORIGIN when branch doesn't exist anywhere."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = [
                MagicMock(returncode=1, stdout="", stderr=""),  # branch doesn't exist locally
                MagicMock(returncode=1, stdout="", stderr=""),  # origin/branch doesn't exist
            ]
            result = operations.check_branch_safe_to_recreate("feature/test")
            assert result.status == operations.BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN
            assert not result.is_safe

    def test_returns_uncommitted_changes_when_on_target_branch_dirty(self, mock_run_safe):
        """Test returns UNCOMMITTED_CHANGES when on the target branch with local changes."""
        with patch.object(operations, "run_git") as mock_run_git:
            with patch.object(operations, "get_current_branch", return_value="feature/test"):
                with patch.object(operations, "has_local_changes", return_value=True):
                    mock_run_git.side_effect = [
                        MagicMock(returncode=0, stdout="abc123", stderr=""),  # branch exists locally
                        MagicMock(returncode=0, stdout="abc123", stderr=""),  # origin/branch exists
                    ]
                    result = operations.check_branch_safe_to_recreate("feature/test")
                    assert result.status == operations.BranchSafetyCheckResult.UNCOMMITTED_CHANGES
                    assert result.has_local_work_at_risk

    def test_returns_safe_when_on_target_branch_clean_matching_origin(self, mock_run_safe):
        """Test returns SAFE when on target branch, clean, and matching origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            with patch.object(operations, "get_current_branch", return_value="feature/test"):
                with patch.object(operations, "has_local_changes", return_value=False):
                    mock_run_git.side_effect = [
                        MagicMock(returncode=0, stdout="abc123", stderr=""),  # branch exists locally
                        MagicMock(returncode=0, stdout="abc123", stderr=""),  # origin/branch exists
                        MagicMock(returncode=0, stdout="abc123\n", stderr=""),  # HEAD commit
                        MagicMock(returncode=0, stdout="abc123\n", stderr=""),  # origin/branch commit
                    ]
                    result = operations.check_branch_safe_to_recreate("feature/test")
                    assert result.status == operations.BranchSafetyCheckResult.SAFE
                    assert result.is_safe

    def test_returns_diverged_when_on_target_branch_clean_different_from_origin(self, mock_run_safe):
        """Test returns DIVERGED_FROM_ORIGIN when on target branch but different from origin."""
        with patch.object(operations, "run_git") as mock_run_git:
            with patch.object(operations, "get_current_branch", return_value="feature/test"):
                with patch.object(operations, "has_local_changes", return_value=False):
                    mock_run_git.side_effect = [
                        MagicMock(returncode=0, stdout="abc123", stderr=""),  # branch exists locally
                        MagicMock(returncode=0, stdout="def456", stderr=""),  # origin/branch exists
                        MagicMock(returncode=0, stdout="abc123\n", stderr=""),  # HEAD commit
                        MagicMock(returncode=0, stdout="def456\n", stderr=""),  # origin/branch commit (different)
                    ]
                    result = operations.check_branch_safe_to_recreate("feature/test")
                    assert result.status == operations.BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN
                    assert result.has_local_work_at_risk


class TestFetchBranch:
    """Tests for fetch_branch function."""

    def test_fetch_branch_success(self, mock_run_safe):
        """Test successful branch fetch."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = operations.fetch_branch("feature/test")

            assert result is True
            mock_run_git.assert_called_once()
            call_args = mock_run_git.call_args[0]
            assert "fetch" in call_args
            assert "origin" in call_args

    def test_fetch_branch_failure(self, mock_run_safe):
        """Test branch fetch failure returns False."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error")

            result = operations.fetch_branch("nonexistent-branch")

            assert result is False

    def test_fetch_branch_dry_run(self, mock_run_safe, capsys):
        """Test dry run doesn't execute fetch."""
        with patch.object(operations, "run_git") as mock_run_git:
            result = operations.fetch_branch("feature/test", dry_run=True)

            mock_run_git.assert_not_called()
            assert result is True
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out

    def test_fetch_branch_exception_propagates(self, mock_run_safe):
        """Test exception during fetch propagates to caller."""
        with patch.object(operations, "run_git") as mock_run_git:
            mock_run_git.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                operations.fetch_branch("feature/test")
