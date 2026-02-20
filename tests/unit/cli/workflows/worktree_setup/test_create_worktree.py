"""Tests for CreateWorktree."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    create_worktree,
)


class TestCreateWorktree:
    """Tests for create_worktree function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_creates_worktree_successfully(self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree):
        """Test successful worktree creation."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False  # Worktree doesn't exist
        mock_run.return_value = MagicMock(returncode=0)
        mock_get_branch.return_value = "main"  # Not on target branch
        mock_in_worktree.return_value = False

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

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_handles_git_worktree_failure(self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree):
        """Test handling git worktree command failure."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_run.return_value = MagicMock(
            returncode=128,
            stderr="fatal: unable to create worktree",
        )

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert result.error_message is not None

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_handles_existing_branch(self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree):
        """Test handling when branch already exists."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        # First call fails with "already exists", second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=128, stderr="branch 'feature/DFLY-1234/implementation' already exists"),
            MagicMock(returncode=0),
        ]

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        assert mock_run.call_count == 2

    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_handles_os_error(self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree):
        """Test handling OS error during worktree creation."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
        mock_run.side_effect = OSError("Permission denied")

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is False
        assert "Error creating worktree" in result.error_message

    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_switches_to_main_when_on_target_branch_in_main_repo(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_switch
    ):
        """Test switches to main when on target branch in main repo (not worktree)."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "feature/DFLY-1234/implementation"
        mock_in_worktree.return_value = False  # In main repo, not worktree
        mock_switch.return_value = True  # Switch succeeds
        mock_run.return_value = MagicMock(returncode=0)

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        mock_switch.assert_called_once()
        mock_run.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_does_not_switch_when_in_worktree(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_switch
    ):
        """Test does NOT switch to main when already in a worktree (even if on same branch)."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "feature/DFLY-1234/implementation"
        mock_in_worktree.return_value = True  # Already in a worktree
        mock_run.return_value = MagicMock(returncode=0)

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

    @patch("agentic_devtools.cli.workflows.worktree_setup.switch_to_main_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_does_not_switch_when_on_different_branch(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_switch
    ):
        """Test does NOT switch when on a different branch than the target."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"  # On main, not the target branch
        mock_in_worktree.return_value = False
        mock_run.return_value = MagicMock(returncode=0)

        result = create_worktree("DFLY-1234", "feature")

        assert result.success is True
        mock_switch.assert_not_called()

    @patch("agentic_devtools.cli.git.operations.check_branch_safe_to_recreate")
    @patch("agentic_devtools.cli.git.operations.fetch_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_use_existing_branch_performs_safety_check(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_fetch, mock_safety_check
    ):
        """Test that use_existing_branch performs safety checks."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
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
    @patch("agentic_devtools.cli.workflows.worktree_setup.is_in_worktree")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_current_branch")
    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("os.path.exists")
    def test_use_existing_branch_tries_tracking_on_failure(
        self, mock_exists, mock_parent, mock_run, mock_get_branch, mock_in_worktree, mock_fetch, mock_safety_check
    ):
        """Test that use_existing_branch tries tracking remote on first failure."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False
        mock_get_branch.return_value = "main"
        mock_in_worktree.return_value = False
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
