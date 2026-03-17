"""Tests for CreateWorktree."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.operations import BranchSafetyCheckResult
from agentic_devtools.cli.workflows.worktree_setup import (
    create_worktree,
)


class TestCreateWorktree:
    """Tests for create_worktree function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_creates_worktree_successfully(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo
    ):
        """Test successful worktree creation."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False  # Worktree doesn't exist
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_branch.return_value = "main"  # Not on target branch
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None  # No identity.json to copy

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        assert "DFLY-1234" in result.worktree_path
        assert result.branch_name == "feature/DFLY-1234/implementation"
        assert result.error_message is None

        # Verify git worktree add was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "worktree" in call_args
        assert "add" in call_args

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    def test_returns_error_when_parent_not_found(self, mock_parent):
        """Test error when parent directory cannot be determined."""
        mock_parent.return_value = None

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert "Could not determine" in result.error_message

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_returns_existing_worktree(self, mock_exists, mock_parent):
        """Test returning existing worktree path."""
        mock_parent.return_value = "/repos"
        # Both worktree path and .git file exist
        mock_exists.side_effect = [True, True]

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        assert "DFLY-1234" in result.worktree_path

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_returns_error_for_directory_not_worktree(self, mock_exists, mock_parent):
        """Test error when directory exists but isn't a git worktree."""
        mock_parent.return_value = "/repos"
        # Worktree path exists, but .git file doesn't
        mock_exists.side_effect = [True, False]

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert "not a git worktree" in result.error_message

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_handles_git_worktree_failure(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo
    ):
        """Test handling git worktree command failure."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: unable to create worktree",
        )

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert result.error_message is not None

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_handles_existing_branch(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo
    ):
        """Test handling when branch already exists."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        # First call fails with "already exists", second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=128, stderr="branch 'feature/DFLY-1234/implementation' already exists"),
            MagicMock(returncode=0),
        ]

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        assert mock_run.call_count == 2

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_handles_os_error(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo
    ):
        """Test handling OS error during worktree creation."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_run.side_effect = OSError("Permission denied")

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert "Error creating worktree" in result.error_message

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_switches_to_main_when_on_target_branch_in_main_repo(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_switch, mock_main_repo
    ):
        """Test switches to main when on target branch in main repo (not worktree)."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "feature/DFLY-1234/implementation"
        mock_in_worktree.return_value = False  # In main repo, not worktree
        mock_switch.return_value = True  # Switch succeeds
        mock_run.return_value = MagicMock(returncode=0)
        mock_main_repo.return_value = None

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        mock_switch.assert_called_once()
        mock_run.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_does_not_switch_when_in_worktree(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_switch, mock_main_repo
    ):
        """Test does NOT switch to main when already in a worktree (even if on same branch)."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "feature/DFLY-1234/implementation"
        mock_in_worktree.return_value = True  # Already in a worktree
        mock_run.return_value = MagicMock(returncode=0)
        mock_main_repo.return_value = None

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        mock_switch.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_fails_when_switch_to_main_fails(
        self, mock_exists, mock_parent, mock_get_branch, mock_in_worktree, mock_switch
    ):
        """Test fails gracefully when switch to main fails."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "feature/DFLY-1234/implementation"
        mock_in_worktree.return_value = False  # In main repo
        mock_switch.return_value = False  # Switch fails

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert "Failed to switch to main branch" in result.error_message

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_does_not_switch_when_on_different_branch(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_switch, mock_main_repo
    ):
        """Test does NOT switch when on a different branch than the target."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"  # On main, not the target branch
        mock_in_worktree.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_main_repo.return_value = None

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        mock_switch.assert_not_called()

    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_use_existing_branch_performs_safety_check(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
    ):
        """Test that use_existing_branch performs safety checks."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = MagicMock(is_safe=True, message="Branch is safe")
        mock_run.return_value = MagicMock(returncode=0)

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
        mock_fetch.assert_called_once_with("feature/DFLY-1234/pr-review")
        mock_safety_check.assert_called_once_with("feature/DFLY-1234/pr-review")

    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_use_existing_branch_fails_when_unsafe(
        self, mock_exists, mock_parent, mock_get_branch, mock_in_worktree, mock_fetch, mock_safety_check
    ):
        """Test that use_existing_branch fails when safety check fails."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = MagicMock(is_safe=False, message="Branch has uncommitted changes")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Cannot safely create worktree" in result.error_message
        assert "Branch has uncommitted changes" in result.error_message

    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_use_existing_branch_tries_tracking_on_failure(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
    ):
        """Test that use_existing_branch tries tracking remote on first failure."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = MagicMock(is_safe=True, message="Safe")
        # First call fails, second succeeds (tracking remote)
        mock_run.side_effect = [
            MagicMock(returncode=128, stderr="fatal: not a valid object name"),
            MagicMock(returncode=0),
        ]

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
        assert mock_run.call_count == 2

    @patch("agentic_devtools.cli.workflows.worktree_setup.shutil.copy2")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_copies_identity_json_to_worktree(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo, mock_copy, tmp_path
    ):
        """Copies identity.json from main repo to new worktree after creation."""
        main_repo_dir = tmp_path / "main"
        main_repo_dir.mkdir()
        agdt_dir = main_repo_dir / ".agdt"
        agdt_dir.mkdir()
        identity_file = agdt_dir / "identity.json"
        identity_file.write_text('{"identity": "ama", "email": "a@b.com"}', encoding="utf-8")

        mock_parent.return_value = str(tmp_path)
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = str(main_repo_dir)

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        mock_copy.assert_called_once()
        call_args = mock_copy.call_args[0]
        assert "identity.json" in call_args[0]
        assert "identity.json" in call_args[1]

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_skips_identity_copy_when_no_main_repo(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo
    ):
        """Does not fail when main repo cannot be determined (no identity to copy)."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None  # No main repo found

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.shutil.copy2")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_identity_copy_exception_is_non_fatal(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_main_repo, mock_copy, tmp_path
    ):
        """An exception during identity.json copy does not fail worktree creation."""
        main_repo_dir = tmp_path / "main"
        main_repo_dir.mkdir()
        agdt_dir = main_repo_dir / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}', encoding="utf-8")

        mock_parent.return_value = str(tmp_path)
        mock_exists.return_value = False
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = str(main_repo_dir)
        mock_copy.side_effect = OSError("permission denied")

        result = create_worktree("DFLY-1234", "feature")

        # Should succeed despite the copy failure
        assert result.success is True

    # -------------------------------------------------------------------------
    # Diverged branch — temp-rename flow (success path)
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.get_short_commit_hash")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_triggers_temp_rename_and_succeeds(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_hash,
        mock_rename,
    ):
        """Diverged branch triggers temp rename; on success renames to PR review name."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Local branch has diverged from origin.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=0)  # worktree add succeeds
        mock_hash.return_value = "abc1234"
        mock_rename.return_value = True  # all renames succeed

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
        # rename should be called at least twice: temp rename + final rename
        assert mock_rename.call_count >= 2
        # First rename: original → temp
        first_call = mock_rename.call_args_list[0]
        assert first_call[0][0] == "feature/DFLY-1234/pr-review"
        assert "-tmp-" in first_call[0][1]
        # Second rename: temp → final PR review name
        second_call = mock_rename.call_args_list[1]
        assert "pr-review" in second_call[0][1]
        assert "abc1234" in second_call[0][1]

    # -------------------------------------------------------------------------
    # Diverged branch — temp-rename flow (worktree creation failure)
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_reverts_temp_rename_on_worktree_failure(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """When worktree creation fails after temp rename, rename is reverted."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Local branch has diverged from origin.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=128, stderr="fatal: could not create")
        mock_rename.return_value = True

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Failed to create worktree" in result.error_message
        # Revert rename: temp → original name
        revert_call = mock_rename.call_args_list[-1]
        assert "-tmp-" in revert_call[0][0]
        assert revert_call[0][1] == "feature/DFLY-1234/pr-review"

    # -------------------------------------------------------------------------
    # Uncommitted changes — temp-rename flow (success path)
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.get_short_commit_hash")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_uncommitted_changes_triggers_temp_rename_and_succeeds(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_hash,
        mock_rename,
    ):
        """Uncommitted changes on local branch triggers same temp-rename flow."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.side_effect = ["main", "feature/DFLY-1234/pr-review"]
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.UNCOMMITTED_CHANGES,
            "You have uncommitted changes.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=0)
        mock_hash.return_value = "deadbeef"
        mock_rename.return_value = True

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
        # Temp rename must have been called
        first_call = mock_rename.call_args_list[0]
        assert first_call[0][0] == "feature/DFLY-1234/pr-review"
        assert "-tmp-" in first_call[0][1]

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_uncommitted_changes_on_different_branch_returns_error(
        self,
        mock_exists,
        mock_parent,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """Uncommitted changes only trigger temp rename when HEAD matches the target branch."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.side_effect = ["main", "feature/DFLY-9999/other-work"]
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.UNCOMMITTED_CHANGES,
            "You have uncommitted changes.",
            "feature/DFLY-1234/pr-review",
        )

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert result.error_message == "Cannot safely create worktree:\nYou have uncommitted changes."
        mock_rename.assert_not_called()

    # -------------------------------------------------------------------------
    # Temp rename itself fails — return error immediately
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_temp_rename_failure_returns_error(
        self,
        mock_exists,
        mock_parent,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """When temp rename fails the setup returns a clear error immediately."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        mock_rename.return_value = False  # rename fails

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Failed to rename" in result.error_message

    # -------------------------------------------------------------------------
    # BRANCH_NOT_ON_ORIGIN with local branch — rename, try, revert, fail
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_branch_not_on_origin_with_local_branch_reverts_and_fails(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """BRANCH_NOT_ON_ORIGIN + local branch: rename, worktree fails, revert rename."""
        mock_parent.return_value = "/repos"
        mock_rename.return_value = True
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN,
            "Branch exists locally but not on origin.",
            "feature/DFLY-1234/pr-review",
        )
        # subprocess.run is called for:
        # 1. rev-parse --verify (local branch check) → returncode=0 (branch exists locally)
        # 2. git worktree add (worktree creation) → fails
        mock_run.side_effect = [
            MagicMock(returncode=0),  # local branch exists
            MagicMock(returncode=128, stderr="fatal: no such ref 'origin/feature/DFLY-1234/pr-review'"),
        ]
        mock_exists.return_value = False

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Failed to create worktree" in result.error_message
        # Rename was called twice: original→temp, then temp→original (revert)
        assert mock_rename.call_count == 2
        revert_call = mock_rename.call_args_list[-1]
        assert revert_call[0][1] == "feature/DFLY-1234/pr-review"

    # -------------------------------------------------------------------------
    # BRANCH_NOT_ON_ORIGIN with no local branch — fail immediately
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_branch_not_on_origin_without_local_branch_fails_immediately(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
    ):
        """BRANCH_NOT_ON_ORIGIN + no local branch: fail without rename."""
        mock_parent.return_value = "/repos"
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN,
            "Branch doesn't exist locally or on origin.",
            "feature/DFLY-1234/pr-review",
        )
        # subprocess.run called for rev-parse --verify → returncode=1 (branch doesn't exist locally)
        mock_run.return_value = MagicMock(returncode=1)
        mock_exists.return_value = False

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Cannot safely create worktree" in result.error_message

    # -------------------------------------------------------------------------
    # BRANCH_NOT_ON_ORIGIN — OSError during local branch existence check
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_branch_not_on_origin_local_check_os_error_treated_as_no_local_branch(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
    ):
        """BRANCH_NOT_ON_ORIGIN + OSError during git rev-parse: treated as no local branch → fail immediately."""
        mock_parent.return_value = "/repos"
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN,
            "Branch doesn't exist on origin.",
            "feature/DFLY-1234/pr-review",
        )
        # subprocess.run raises OSError (e.g., git not found)
        mock_run.side_effect = OSError("git not found")
        mock_exists.return_value = False

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        # OSError treated as "no local branch" → fall through to immediate fail
        assert result.success is False
        assert "Cannot safely create worktree" in result.error_message

    # -------------------------------------------------------------------------
    # SAFE branch but "already checked out" — delete+retry flow
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.delete_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_safe_branch_already_checked_out_deletes_and_retries(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_delete,
    ):
        """SAFE branch with 'already checked out' error: deletes local ref and retries."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.SAFE,
            "Branch is safe.",
            "feature/DFLY-1234/pr-review",
        )
        mock_delete.return_value = True
        # First call fails with "already checked out", second is git worktree prune, third (tracking) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=128, stderr="fatal: 'feature/DFLY-1234/pr-review' is already checked out"),
            MagicMock(returncode=0),  # git worktree prune
            MagicMock(returncode=0),  # retry with --track
        ]

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
        mock_delete.assert_called_once_with("feature/DFLY-1234/pr-review", force=True)
        assert mock_run.call_count == 3

    # -------------------------------------------------------------------------
    # SAFE branch "already checked out" — delete fails → return clear error
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.delete_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_safe_branch_already_checked_out_delete_fails_returns_error(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_delete,
    ):
        """SAFE branch 'already checked out' but delete fails: return clear error, no retry."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.SAFE,
            "Branch is safe.",
            "feature/DFLY-1234/pr-review",
        )
        mock_delete.return_value = False  # delete fails
        # First call fails with "already checked out", second is git worktree prune
        mock_run.side_effect = [
            MagicMock(returncode=128, stderr="fatal: 'feature/DFLY-1234/pr-review' is already checked out"),
            MagicMock(returncode=0),  # git worktree prune (non-fatal)
        ]

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "already checked out" in result.error_message.lower()
        # 1 initial add + 1 prune; no retry after failed delete
        assert mock_run.call_count == 2

    # -------------------------------------------------------------------------
    # Diverged branch — OSError during subprocess.run in temp-rename flow
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_os_error_reverts_rename(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """OSError during worktree add in temp-rename flow: revert rename and fail."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        mock_rename.return_value = True
        mock_run.side_effect = OSError("git not found")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Error creating worktree" in result.error_message
        # Revert rename: temp → original
        revert_call = mock_rename.call_args_list[-1]
        assert revert_call[0][1] == "feature/DFLY-1234/pr-review"

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_os_error_revert_also_fails_includes_warning(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """OSError during worktree add AND revert fails: error message includes recovery hint."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        # First rename (temp) succeeds, revert rename fails
        mock_rename.side_effect = [True, False]
        mock_run.side_effect = OSError("git not found")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Error creating worktree" in result.error_message
        assert "Warning: Failed to revert branch rename" in result.error_message
        assert "git branch -m" in result.error_message

    # -------------------------------------------------------------------------
    # Diverged branch — worktree creation fails AND revert fails
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_revert_also_fails_includes_warning(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """When worktree creation fails and revert rename also fails, warning included in error."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        # First rename (temp) succeeds, revert rename fails
        mock_rename.side_effect = [True, False]
        mock_run.return_value = MagicMock(returncode=128, stderr="fatal: could not create worktree")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Failed to create worktree" in result.error_message
        assert "Warning: Failed to revert branch rename" in result.error_message
        assert "git branch -m" in result.error_message

    # -------------------------------------------------------------------------
    # Diverged branch — OSError from rename_local_branch during revert (OSError handler path)
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_os_error_revert_raises_os_error(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """OSError during worktree add AND revert also raises OSError: recovery hint still included."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        # First rename (original→temp) succeeds; second (revert) raises OSError
        mock_rename.side_effect = [True, OSError("git missing")]
        mock_run.side_effect = OSError("git not found")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Error creating worktree" in result.error_message
        assert "revert also failed" in result.error_message
        assert "Warning: Failed to revert branch rename" in result.error_message
        assert "git branch -m" in result.error_message

    # -------------------------------------------------------------------------
    # Diverged branch — OSError from rename_local_branch during revert (failure path)
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_worktree_fail_revert_raises_os_error(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_fetch,
        mock_safety_check,
        mock_rename,
    ):
        """Worktree creation fails AND revert rename raises OSError: recovery hint still included."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        # First rename (original→temp) succeeds; revert raises OSError
        mock_rename.side_effect = [True, OSError("git missing")]
        mock_run.return_value = MagicMock(returncode=128, stderr="fatal: could not create worktree")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is False
        assert "Failed to create worktree" in result.error_message
        assert "revert also failed" in result.error_message
        assert "Warning: Failed to revert branch rename" in result.error_message
        assert "git branch -m" in result.error_message

    # -------------------------------------------------------------------------
    # Diverged branch — OSError from get_short_commit_hash on success path → non-fatal
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.get_short_commit_hash")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_success_path_os_error_in_final_rename_block_is_non_fatal(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_hash,
        mock_rename,
    ):
        """OSError from get_short_commit_hash on success path: worktree still returned as success."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=0)
        # get_short_commit_hash raises; the try/except must swallow it and return success
        mock_hash.side_effect = OSError("git missing")
        mock_rename.return_value = True

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True

    # -------------------------------------------------------------------------
    # Diverged branch — final rename (temp → PR review name) fails → warning logged
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.get_short_commit_hash")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_final_rename_failure_warns_but_succeeds(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_hash,
        mock_rename,
    ):
        """When final rename to PR-review-name fails, a warning is logged but setup succeeds."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = None
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=0)
        mock_hash.return_value = "abc1234"
        # First rename (original→temp) succeeds, final rename (temp→pr-review) fails
        mock_rename.side_effect = [True, False]

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True

    # -------------------------------------------------------------------------
    # Diverged branch success path — identity propagation exercised
    # -------------------------------------------------------------------------

    @patch("agentic_devtools.cli.workflows.worktree_setup.shutil.copy2")
    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.get_short_commit_hash")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_success_propagates_identity_json(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_hash,
        mock_rename,
        mock_copy,
        tmp_path,
    ):
        """Diverged branch success path copies identity.json to the new worktree."""
        main_repo_dir = tmp_path / "main"
        main_repo_dir.mkdir()
        agdt_dir = main_repo_dir / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}', encoding="utf-8")

        mock_parent.return_value = str(tmp_path)
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = str(main_repo_dir)
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=0)
        mock_hash.return_value = "abc1234"
        mock_rename.return_value = True

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
        mock_copy.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.shutil.copy2")
    @patch("agentic_devtools.cli.git.operations.rename_local_branch")
    @patch("agentic_devtools.cli.git.operations.get_short_commit_hash")
    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_diverged_branch_identity_copy_exception_is_non_fatal(
        self,
        mock_exists,
        mock_parent,
        mock_run,
        mock_get_branch,
        mock_in_worktree,
        mock_main_repo,
        mock_fetch,
        mock_safety_check,
        mock_hash,
        mock_rename,
        mock_copy,
        tmp_path,
    ):
        """An exception during identity.json copy in temp-rename path doesn't fail setup."""
        main_repo_dir = tmp_path / "main"
        main_repo_dir.mkdir()
        agdt_dir = main_repo_dir / ".agdt"
        agdt_dir.mkdir()
        (agdt_dir / "identity.json").write_text('{"identity": "ama", "email": "a@b.com"}', encoding="utf-8")

        mock_parent.return_value = str(tmp_path)
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_main_repo.return_value = str(main_repo_dir)
        mock_safety_check.return_value = BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            "Diverged.",
            "feature/DFLY-1234/pr-review",
        )
        mock_run.return_value = MagicMock(returncode=0)
        mock_hash.return_value = "abc1234"
        mock_rename.return_value = True
        mock_copy.side_effect = OSError("permission denied")

        result = create_worktree(
            "DFLY-1234", "feature", branch_name="feature/DFLY-1234/pr-review", use_existing_branch=True
        )

        assert result.success is True
