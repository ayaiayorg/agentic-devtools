"""Tests for worktree_setup module."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import (
    PlaceholderIssueResult,
    WorktreeSetupResult,
    check_worktree_exists,
    create_placeholder_and_setup_worktree,
    create_placeholder_issue,
    create_worktree,
    generate_workflow_branch_name,
    get_ai_agent_continuation_prompt,
    get_current_branch,
    get_main_repo_root,
    get_repos_parent_dir,
    get_worktree_continuation_prompt,
    is_in_worktree,
    open_vscode_workspace,
    setup_worktree_environment,
    setup_worktree_in_background_sync,
    start_worktree_setup_background,
    switch_to_main_branch,
)


class TestWorktreeSetupResult:
    """Tests for WorktreeSetupResult dataclass."""

    def test_required_fields(self):
        """Test required fields for WorktreeSetupResult."""
        result = WorktreeSetupResult(
            success=True,
            worktree_path="/path/to/worktree",
            branch_name="feature/DFLY-1234/test",
        )
        assert result.success is True
        assert result.worktree_path == "/path/to/worktree"
        assert result.branch_name == "feature/DFLY-1234/test"
        # Default values for optional fields
        assert result.error_message is None
        assert result.vscode_opened is False

    def test_custom_values(self):
        """Test custom values for WorktreeSetupResult."""
        result = WorktreeSetupResult(
            success=True,
            worktree_path="/path/to/worktree",
            branch_name="feature/DFLY-1234/test",
            vscode_opened=True,
            error_message=None,
        )
        assert result.success is True
        assert result.worktree_path == "/path/to/worktree"
        assert result.branch_name == "feature/DFLY-1234/test"
        assert result.vscode_opened is True
        assert result.error_message is None

    def test_error_state(self):
        """Test error state with message."""
        result = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Failed to create worktree",
        )
        assert result.success is False
        assert result.error_message == "Failed to create worktree"


class TestPlaceholderIssueResult:
    """Tests for PlaceholderIssueResult dataclass."""

    def test_default_values(self):
        """Test default values for PlaceholderIssueResult."""
        result = PlaceholderIssueResult(success=False)
        assert result.success is False
        assert result.issue_key is None
        assert result.error_message is None

    def test_success_state(self):
        """Test success state with issue key."""
        result = PlaceholderIssueResult(
            success=True,
            issue_key="DFLY-1234",
        )
        assert result.success is True
        assert result.issue_key == "DFLY-1234"
        assert result.error_message is None

    def test_error_state(self):
        """Test error state with message."""
        result = PlaceholderIssueResult(
            success=False,
            error_message="API returned 401",
        )
        assert result.success is False
        assert result.issue_key is None
        assert result.error_message == "API returned 401"


class TestGetMainRepoRoot:
    """Tests for get_main_repo_root function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_main_repo_root_from_worktree(self, mock_run):
        """Test returning main repo root when in a worktree."""
        # Mock subprocess to return a .git directory path (indicating worktree)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="/repos/main-repo/.git/worktrees/DFLY-1234\n",
        )

        result = get_main_repo_root()

        # Result should be parent of .git directory
        assert "main-repo" in result or "repos" in result
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--git-common-dir"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_main_repo_root_from_main_repo(self, mock_run):
        """Test returning main repo root when in the main repo."""
        # Mock subprocess to return .git (indicating main repo)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=".git\n",
        )

        with patch("os.getcwd", return_value="/repos/main-repo"):
            result = get_main_repo_root()

        # Result should contain the repo path
        assert result is not None
        assert "main-repo" in result or "repos" in result

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_file_not_found(self, mock_run):
        """Test returning None when git not found."""
        mock_run.side_effect = FileNotFoundError("git not found")

        result = get_main_repo_root()

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_os_error(self, mock_run):
        """Test returning None on OS error."""
        mock_run.side_effect = OSError("Some OS error")

        result = get_main_repo_root()

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_nonzero_return_code(self, mock_run):
        """Test returning None when git returns non-zero."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        result = get_main_repo_root()

        assert result is None


class TestGetReposParentDir:
    """Tests for get_repos_parent_dir function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    def test_returns_parent_dir_of_main_repo(self, mock_get_main):
        """Test returning parent directory of main repo."""
        mock_get_main.return_value = "/repos/main-repo"

        result = get_repos_parent_dir()

        # On Windows, Path normalizes slashes
        assert "repos" in result

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_main_repo_root")
    def test_returns_none_when_main_repo_not_found(self, mock_get_main):
        """Test returning None when main repo cannot be found."""
        mock_get_main.return_value = None

        result = get_repos_parent_dir()

        assert result is None


class TestIsInWorktree:
    """Tests for is_in_worktree function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_true_in_worktree(self, mock_run):
        """Test returns True when in a worktree (git-dir != git-common-dir)."""
        # In a worktree, git-dir points to .git/worktrees/<name>
        # while git-common-dir points to the main repo's .git
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="/repos/main/.git/worktrees/DFLY-1234"),
            MagicMock(returncode=0, stdout="/repos/main/.git"),
        ]

        result = is_in_worktree()

        assert result is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_in_main_repo(self, mock_run):
        """Test returns False when in main repo (git-dir == git-common-dir)."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=".git"),
            MagicMock(returncode=0, stdout=".git"),
        ]

        result = is_in_worktree()

        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_git_error(self, mock_run):
        """Test returns False when git commands fail."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a git repo")

        result = is_in_worktree()

        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_file_not_found(self, mock_run):
        """Test returns False when git is not installed."""
        mock_run.side_effect = FileNotFoundError("git not found")

        result = is_in_worktree()

        assert result is False


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_branch_name(self, mock_run):
        """Test returns current branch name."""
        mock_run.return_value = MagicMock(returncode=0, stdout="feature/DFLY-1234/implementation\n")

        result = get_current_branch()

        assert result == "feature/DFLY-1234/implementation"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_detached_head(self, mock_run):
        """Test returns None on detached HEAD."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = get_current_branch()

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_git_error(self, mock_run):
        """Test returns None on git error."""
        mock_run.return_value = MagicMock(returncode=128, stdout="")

        result = get_current_branch()

        assert result is None


class TestSwitchToMainBranch:
    """Tests for switch_to_main_branch function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_true_on_success(self, mock_run):
        """Test returns True when switch succeeds."""
        mock_run.return_value = MagicMock(returncode=0)

        result = switch_to_main_branch()

        assert result is True
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["git", "switch", "main"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_failure(self, mock_run):
        """Test returns False when switch fails."""
        mock_run.return_value = MagicMock(returncode=1)

        result = switch_to_main_branch()

        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_false_on_os_error(self, mock_run):
        """Test returns False on OS error."""
        mock_run.side_effect = OSError("git not accessible")

        result = switch_to_main_branch()

        assert result is False


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


class TestSetupWorktreeFromState:
    """Tests for _setup_worktree_from_state function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_reads_parameters_from_state(self, mock_get_value, mock_setup_sync):
        """Test that parameters are read from state correctly."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-5678",
            "worktree_setup.branch_prefix": "bugfix",
            "worktree_setup.branch_name": "feature/DFLY-5678/test",
            "worktree_setup.use_existing_branch": "true",
            "worktree_setup.workflow_name": "pull-request-review",
            "worktree_setup.user_request": "Review this PR",
            "worktree_setup.additional_params": '{"pr_id": "123"}',
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        mock_setup_sync.assert_called_once_with(
            issue_key="DFLY-5678",
            branch_prefix="bugfix",
            branch_name="feature/DFLY-5678/test",
            use_existing_branch=True,
            workflow_name="pull-request-review",
            user_request="Review this PR",
            additional_params={"pr_id": "123"},
        )

    @patch("agentic_devtools.state.get_value")
    def test_raises_error_when_issue_key_missing(self, mock_get_value):
        """Test that ValueError is raised when issue_key is missing."""
        mock_get_value.return_value = None

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        with pytest.raises(ValueError, match="worktree_setup.issue_key not set"):
            _setup_worktree_from_state()

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_handles_invalid_json_in_additional_params(self, mock_get_value, mock_setup_sync):
        """Test that invalid JSON in additional_params is handled gracefully."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-1234",
            "worktree_setup.branch_prefix": "feature",
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": "false",
            "worktree_setup.workflow_name": "work-on-jira-issue",
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": "invalid json {",
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        mock_setup_sync.assert_called_once()
        call_kwargs = mock_setup_sync.call_args[1]
        assert call_kwargs["additional_params"] is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_in_background_sync")
    @patch("agentic_devtools.state.get_value")
    def test_uses_default_values_when_not_set(self, mock_get_value, mock_setup_sync):
        """Test that default values are used when state values are not set."""
        mock_get_value.side_effect = lambda key: {
            "worktree_setup.issue_key": "DFLY-9999",
            "worktree_setup.branch_prefix": None,  # Should default to "feature"
            "worktree_setup.branch_name": None,
            "worktree_setup.use_existing_branch": None,  # Should default to False
            "worktree_setup.workflow_name": None,  # Should default to "work-on-jira-issue"
            "worktree_setup.user_request": None,
            "worktree_setup.additional_params": None,
        }.get(key)

        from agentic_devtools.cli.workflows.worktree_setup import _setup_worktree_from_state

        _setup_worktree_from_state()

        mock_setup_sync.assert_called_once_with(
            issue_key="DFLY-9999",
            branch_prefix="feature",
            branch_name=None,
            use_existing_branch=False,
            workflow_name="work-on-jira-issue",
            user_request=None,
            additional_params=None,
        )



class TestOpenVscodeWorkspace:
    """Tests for open_vscode_workspace function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_opens_vscode_on_windows(self, mock_exists, mock_platform, mock_popen):
        """Test opening VS Code on Windows."""
        mock_exists.return_value = True
        mock_platform.return_value = "Windows"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "code" in call_args[0].lower() or any("code" in str(arg).lower() for arg in call_args)

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_opens_vscode_on_linux(self, mock_exists, mock_platform, mock_popen):
        """Test opening VS Code on Linux."""
        mock_exists.return_value = True
        mock_platform.return_value = "Linux"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_opens_vscode_on_darwin(self, mock_exists, mock_platform, mock_popen):
        """Test opening VS Code on macOS."""
        mock_exists.return_value = True
        mock_platform.return_value = "Darwin"
        mock_popen.return_value = MagicMock()

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is True
        mock_popen.assert_called_once()

    @patch("os.path.exists")
    def test_returns_false_when_workspace_not_found(self, mock_exists):
        """Test returning False when workspace file not found."""
        mock_exists.return_value = False

        result = open_vscode_workspace("/repos/DFLY-1234")

        # Should return False since workspace doesn't exist
        assert result is False

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.Popen")
    @patch("agentic_devtools.cli.workflows.worktree_setup.platform.system")
    @patch("os.path.exists")
    def test_handles_popen_exception(self, mock_exists, mock_platform, mock_popen):
        """Test handling Popen exception."""
        mock_exists.return_value = True
        mock_platform.return_value = "Windows"
        mock_popen.side_effect = OSError("code not found")

        result = open_vscode_workspace("/repos/DFLY-1234")

        assert result is False


class TestSetupWorktreeEnvironment:
    """Tests for setup_worktree_environment function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_full_setup_success(self, mock_create, mock_vscode):
        """Test successful full environment setup."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )
        mock_vscode.return_value = True

        result = setup_worktree_environment(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            open_vscode=True,
        )

        assert result.success is True
        assert result.worktree_path == "/repos/DFLY-1234"
        assert result.branch_name == "feature/DFLY-1234/implementation"
        assert result.vscode_opened is True

    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_setup_fails_when_worktree_fails(self, mock_create):
        """Test setup failure when worktree creation fails."""
        mock_create.return_value = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Git error",
        )

        result = setup_worktree_environment(issue_key="DFLY-1234")

        assert result.success is False
        assert "Git error" in result.error_message

    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_setup_without_vscode(self, mock_create, mock_vscode):
        """Test setup without opening VS Code."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )

        result = setup_worktree_environment(
            issue_key="DFLY-1234",
            open_vscode=False,
        )

        assert result.success is True
        assert result.vscode_opened is False
        mock_vscode.assert_not_called()


class TestCheckWorktreeExists:
    """Tests for check_worktree_exists function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("agentic_devtools.cli.workflows.worktree_setup.os.path.exists")
    def test_returns_path_when_worktree_exists(self, mock_exists, mock_parent):
        """Test returning path when worktree exists."""
        mock_parent.return_value = "/repos"
        # First call: worktree path exists, Second call: .git file exists
        mock_exists.side_effect = [True, True]

        result = check_worktree_exists("DFLY-1234")

        assert "DFLY-1234" in result

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("agentic_devtools.cli.workflows.worktree_setup.os.path.exists")
    def test_returns_none_when_worktree_not_exists(self, mock_exists, mock_parent):
        """Test returning None when worktree doesn't exist."""
        mock_parent.return_value = "/repos"
        mock_exists.return_value = False

        result = check_worktree_exists("DFLY-1234")

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    def test_returns_none_when_parent_not_found(self, mock_parent):
        """Test returning None when parent directory not found."""
        mock_parent.return_value = None

        result = check_worktree_exists("DFLY-1234")

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_repos_parent_dir")
    @patch("agentic_devtools.cli.workflows.worktree_setup.os.path.exists")
    def test_returns_none_when_not_valid_git_worktree(self, mock_exists, mock_parent):
        """Test returning None when directory exists but isn't a git worktree."""
        mock_parent.return_value = "/repos"
        # First call: worktree path exists, Second call: .git file doesn't exist
        mock_exists.side_effect = [True, False]

        result = check_worktree_exists("DFLY-1234")

        assert result is None


class TestGetWorktreeContinuationPrompt:
    """Tests for get_worktree_continuation_prompt function."""

    def test_generates_work_on_jira_issue_prompt(self):
        """Test generating prompt for work-on-jira-issue workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="work-on-jira-issue",
        )

        assert "DFLY-1234" in result
        assert "agdt-initiate-work-on-jira-issue-workflow" in result
        assert "--issue-key DFLY-1234" in result

    def test_generates_pull_request_review_prompt(self):
        """Test generating prompt for pull-request-review workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-5678",
            workflow_name="pull-request-review",
        )

        assert "DFLY-5678" in result
        assert "agdt-initiate-pull-request-review-workflow" in result

    def test_generates_create_jira_issue_prompt(self):
        """Test generating prompt for create-jira-issue workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-issue",
        )

        assert "agdt-initiate-create-jira-issue-workflow" in result

    def test_includes_user_request_parameter(self):
        """Test including user request in the prompt."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-issue",
            user_request="Create a new feature for the dashboard",
        )

        assert "--user-request" in result
        assert "Create a new feature for the dashboard" in result

    def test_escapes_quotes_in_user_request(self):
        """Test that quotes are escaped in user request."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-issue",
            user_request='Create a "special" feature',
        )

        # Quotes should be escaped
        assert '\\"special\\"' in result or "special" in result

    def test_includes_additional_params(self):
        """Test including additional parameters in the prompt."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-subtask",
            additional_params={"parent_key": "DFLY-1000"},
        )

        assert "--parent-key" in result
        assert "DFLY-1000" in result

    def test_includes_pull_request_id_param(self):
        """Test including pull request ID parameter."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            additional_params={"pull_request_id": "12345"},
        )

        assert "--pull-request-id" in result
        assert "12345" in result

    def test_returns_generic_prompt_for_unknown_workflow(self):
        """Test returning generic prompt for unknown workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="unknown-workflow",
        )

        assert "DFLY-1234" in result
        assert "new VS Code window" in result

    def test_generate_create_jira_epic_prompt(self):
        """Test generating prompt for create-jira-epic workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-epic",
        )

        assert "agdt-initiate-create-jira-epic-workflow" in result

    def test_generate_create_jira_subtask_prompt(self):
        """Test generating prompt for create-jira-subtask workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="create-jira-subtask",
        )

        assert "agdt-initiate-create-jira-subtask-workflow" in result

    def test_generate_update_jira_issue_prompt(self):
        """Test generating prompt for update-jira-issue workflow."""
        result = get_worktree_continuation_prompt(
            issue_key="DFLY-1234",
            workflow_name="update-jira-issue",
        )

        assert "agdt-initiate-update-jira-issue-workflow" in result


class TestCreatePlaceholderIssue:
    """Tests for create_placeholder_issue function."""

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_creates_task_successfully(self, mock_create):
        """Test creating a placeholder task successfully."""
        mock_create.return_value = {"key": "DFLY-1234"}

        result = create_placeholder_issue(project_key="DFLY", issue_type="Task")

        assert result.success is True
        assert result.issue_key == "DFLY-1234"
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["project_key"] == "DFLY"
        assert call_kwargs["issue_type"] == "Task"
        assert "placeholder" in call_kwargs["summary"].lower()

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_creates_epic_with_epic_name(self, mock_create):
        """Test creating a placeholder epic with epic name."""
        mock_create.return_value = {"key": "DFLY-5678"}

        result = create_placeholder_issue(project_key="DFLY", issue_type="Epic")

        assert result.success is True
        assert result.issue_key == "DFLY-5678"
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["issue_type"] == "Epic"
        assert call_kwargs["epic_name"] is not None

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_creates_subtask_with_parent(self, mock_create):
        """Test creating a placeholder subtask with parent key."""
        mock_create.return_value = {"key": "DFLY-1235"}

        result = create_placeholder_issue(
            project_key="DFLY",
            issue_type="Sub-task",
            parent_key="DFLY-1234",
        )

        assert result.success is True
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["parent_key"] == "DFLY-1234"

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_handles_missing_key_in_response(self, mock_create):
        """Test handling response without issue key."""
        mock_create.return_value = {}  # No key in response

        result = create_placeholder_issue(project_key="DFLY")

        assert result.success is False
        assert "did not return" in result.error_message.lower()

    @patch("agentic_devtools.cli.jira.create_commands.create_issue_sync")
    def test_handles_api_exception(self, mock_create):
        """Test handling API exception."""
        mock_create.side_effect = Exception("API connection failed")

        result = create_placeholder_issue(project_key="DFLY")

        assert result.success is False
        assert "API connection failed" in result.error_message


class TestCreatePlaceholderAndSetupWorktree:
    """Tests for create_placeholder_and_setup_worktree function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue")
    def test_full_workflow_success(
        self,
        mock_create_issue,
        mock_set_value,
        mock_check_exists,
        mock_setup,
        mock_prompt,
    ):
        """Test successful full workflow - create issue and setup worktree."""
        mock_create_issue.return_value = PlaceholderIssueResult(success=True, issue_key="DFLY-9999")
        mock_check_exists.return_value = None  # No existing worktree
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-9999",
            branch_name="feature/DFLY-9999/implementation",
            vscode_opened=True,
        )
        mock_prompt.return_value = "Continue command..."

        success, issue_key = create_placeholder_and_setup_worktree(
            project_key="DFLY",
            issue_type="Task",
            workflow_name="create-jira-issue",
        )

        assert success is True
        assert issue_key == "DFLY-9999"
        mock_set_value.assert_called_with("jira.issue_key", "DFLY-9999")
        mock_setup.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue")
    def test_fails_when_issue_creation_fails(self, mock_create_issue):
        """Test failure when issue creation fails."""
        mock_create_issue.return_value = PlaceholderIssueResult(success=False, error_message="API error")

        success, issue_key = create_placeholder_and_setup_worktree(
            project_key="DFLY",
            issue_type="Task",
        )

        assert success is False
        assert issue_key is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue")
    def test_uses_existing_worktree(
        self,
        mock_create_issue,
        mock_set_value,
        mock_check_exists,
        mock_vscode,
        mock_prompt,
    ):
        """Test using existing worktree when it already exists."""
        mock_create_issue.return_value = PlaceholderIssueResult(success=True, issue_key="DFLY-9999")
        mock_check_exists.return_value = "/repos/DFLY-9999"  # Worktree exists
        mock_vscode.return_value = True
        mock_prompt.return_value = "Continue command..."

        success, issue_key = create_placeholder_and_setup_worktree(
            project_key="DFLY",
            issue_type="Task",
        )

        assert success is True
        assert issue_key == "DFLY-9999"
        # Should open vscode for existing worktree
        mock_vscode.assert_called_once()

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue")
    def test_returns_issue_key_even_when_worktree_fails(
        self,
        mock_create_issue,
        mock_set_value,
        mock_check_exists,
        mock_setup,
        mock_prompt,
    ):
        """Test returning issue key even when worktree setup fails."""
        mock_create_issue.return_value = PlaceholderIssueResult(success=True, issue_key="DFLY-9999")
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Git worktree failed",
        )

        success, issue_key = create_placeholder_and_setup_worktree(
            project_key="DFLY",
            issue_type="Task",
        )

        # Should return False but still have the issue_key
        assert success is False
        assert issue_key == "DFLY-9999"

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_placeholder_issue")
    def test_passes_user_request_to_prompt(
        self,
        mock_create_issue,
        mock_set_value,
        mock_check_exists,
        mock_setup,
        mock_prompt,
    ):
        """Test passing user request to continuation prompt."""
        mock_create_issue.return_value = PlaceholderIssueResult(success=True, issue_key="DFLY-9999")
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-9999",
            branch_name="feature/DFLY-9999/implementation",
        )
        mock_prompt.return_value = "Continue..."

        create_placeholder_and_setup_worktree(
            project_key="DFLY",
            issue_type="Task",
            workflow_name="create-jira-issue",
            user_request="Create a feature for X",
            additional_params={"parent_key": "DFLY-1000"},
        )

        mock_prompt.assert_called_with(
            "DFLY-9999",
            "create-jira-issue",
            "Create a feature for X",
            {"parent_key": "DFLY-1000"},
        )


class TestGetAiAgentContinuationPrompt:
    """Tests for get_ai_agent_continuation_prompt function."""

    def test_contains_issue_key(self):
        """Test that prompt contains the issue key."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "DFLY-1234" in prompt

    def test_contains_workflow_command(self):
        """Test that prompt contains the workflow initiation command."""
        prompt = get_ai_agent_continuation_prompt("DFLY-5678")
        assert "agdt-initiate-work-on-jira-issue-workflow --issue-key DFLY-5678" in prompt

    def test_contains_senior_engineer_role(self):
        """Test that prompt establishes senior engineer role."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "senior software engineer" in prompt
        assert "expert architect" in prompt

    def test_contains_independence_instructions(self):
        """Test that prompt instructs AI to work independently."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "Work as independently as possible" in prompt
        assert "only pausing to ask questions or seek approval if absolutely necessary" in prompt

    def test_contains_auto_approval_hint(self):
        """Test that prompt mentions auto-approved commands."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "auto approved" in prompt

    def test_contains_review_assurance(self):
        """Test that prompt mentions PR review by colleague."""
        prompt = get_ai_agent_continuation_prompt("DFLY-1234")
        assert "thoroughly review your work" in prompt
        assert "trusted colleague" in prompt

    def test_different_issue_keys_produce_different_prompts(self):
        """Test that different issue keys produce different prompts."""
        prompt1 = get_ai_agent_continuation_prompt("DFLY-1111")
        prompt2 = get_ai_agent_continuation_prompt("DFLY-2222")
        assert prompt1 != prompt2
        assert "DFLY-1111" in prompt1
        assert "DFLY-2222" in prompt2
        assert "DFLY-2222" not in prompt1
        assert "DFLY-1111" not in prompt2

    def test_returns_string(self):
        """Test that the function returns a string."""
        prompt = get_ai_agent_continuation_prompt("TEST-123")
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be a substantial prompt

    def test_pull_request_review_uses_pull_request_id_parameter(self):
        """Test that PR review workflow uses --pull-request-id instead of --issue-key."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PR24031",
            workflow_name="pull-request-review",
            additional_params={"pull_request_id": "24031"},
        )
        assert "--pull-request-id 24031" in prompt
        assert "--issue-key PR24031" not in prompt
        assert "agdt-initiate-pull-request-review-workflow" in prompt

    def test_pull_request_review_falls_back_to_issue_key_without_additional_params(self):
        """Test that PR review falls back to issue-key if no additional_params provided."""
        prompt = get_ai_agent_continuation_prompt(
            issue_key="PR24031",
            workflow_name="pull-request-review",
        )
        # Without additional_params, should fall back to --issue-key
        assert "--issue-key PR24031" in prompt
        assert "--pull-request-id" not in prompt

    def test_other_workflows_still_use_issue_key(self):
        """Test that non-PR workflows still use --issue-key."""
        for workflow in ["work-on-jira-issue", "update-jira-issue", "create-jira-issue"]:
            prompt = get_ai_agent_continuation_prompt(
                issue_key="DFLY-1234",
                workflow_name=workflow,
                additional_params={"pull_request_id": "99999"},  # Should be ignored
            )
            assert "--issue-key DFLY-1234" in prompt
            assert "--pull-request-id" not in prompt


class TestSetupWorktreeInBackgroundSync:
    """Tests for setup_worktree_in_background_sync function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_existing_worktree_reuses_and_opens(
        self,
        mock_check_exists,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        capsys,
    ):
        """Test that existing worktree is reused and opened."""
        mock_check_exists.return_value = "/repos/DFLY-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        mock_check_exists.assert_called_once_with("DFLY-1234")
        mock_open_vscode.assert_called_once_with("/repos/DFLY-1234")
        captured = capsys.readouterr()
        assert "Worktree already exists" in captured.out
        assert "Environment ready!" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_new_worktree_created_successfully(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        capsys,
    ):
        """Test that new worktree is created when none exists."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
            vscode_opened=True,
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        mock_check_exists.assert_called_once_with("DFLY-1234")
        mock_setup.assert_called_once()
        captured = capsys.readouterr()
        assert "Creating worktree" in captured.out
        assert "Environment setup complete!" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_setup_failure_raises_runtime_error(
        self,
        mock_check_exists,
        mock_setup,
    ):
        """Test that setup failure raises RuntimeError."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Git worktree command failed",
        )

        with pytest.raises(RuntimeError) as exc_info:
            setup_worktree_in_background_sync(
                issue_key="DFLY-1234",
                branch_prefix="feature",
                workflow_name="work-on-jira-issue",
            )

        assert "Git worktree command failed" in str(exc_info.value)

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_passes_user_request_to_prompt(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
    ):
        """Test that user_request is passed to continuation prompt."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
            user_request="Create a feature for X",
            additional_params={"parent_key": "DFLY-1000"},
        )

        mock_continuation_prompt.assert_called_with(
            "DFLY-1234",
            "create-jira-issue",
            "Create a feature for X",
            {"parent_key": "DFLY-1000"},
        )


class TestStartWorktreeSetupBackground:
    """Tests for start_worktree_setup_background function."""

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_starts_background_task_with_basic_params(self, mock_run_background, mock_set_value):
        """Test starting background task with basic parameters."""
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_run_background.return_value = mock_task

        result = start_worktree_setup_background(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        assert result == "task-123"
        mock_run_background.assert_called_once()
        call_kwargs = mock_run_background.call_args[1]
        assert call_kwargs["module_path"] == "agentic_devtools.cli.workflows.worktree_setup"
        assert call_kwargs["function_name"] == "_setup_worktree_from_state"
        assert "agdt-setup-worktree-background" in call_kwargs["command_display_name"]
        assert "--issue-key DFLY-1234" in call_kwargs["command_display_name"]

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_includes_user_request_when_provided(self, mock_run_background, mock_set_value):
        """Test that user_request is stored in state when provided."""
        mock_task = MagicMock()
        mock_task.id = "task-456"
        mock_run_background.return_value = mock_task

        result = start_worktree_setup_background(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
            user_request="Create a feature for testing",
        )

        assert result == "task-456"
        # Verify user_request was stored in state
        mock_set_value.assert_any_call("worktree_setup.user_request", "Create a feature for testing")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_includes_additional_params_when_provided(self, mock_run_background, mock_set_value):
        """Test that additional_params is stored in state when provided."""
        mock_task = MagicMock()
        mock_task.id = "task-789"
        mock_run_background.return_value = mock_task

        result = start_worktree_setup_background(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
            additional_params={"parent_key": "DFLY-1000"},
        )

        assert result == "task-789"
        # Verify additional_params was stored in state as JSON
        import json

        expected_json = json.dumps({"parent_key": "DFLY-1000"})
        mock_set_value.assert_any_call("worktree_setup.additional_params", expected_json)

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_basic_params_in_state(self, mock_run_background, mock_set_value):
        """Test that basic params are stored in state."""
        mock_task = MagicMock()
        mock_task.id = "task-esc"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
        )

        # Verify basic params were stored in state
        mock_set_value.assert_any_call("worktree_setup.issue_key", "DFLY-1234")
        mock_set_value.assert_any_call("worktree_setup.branch_prefix", "feature")
        mock_set_value.assert_any_call("worktree_setup.workflow_name", "create-jira-issue")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_passes_correct_args_to_background_task(self, mock_run_background, mock_set_value):
        """Test that correct args dict is passed to run_function_in_background."""
        mock_task = MagicMock()
        mock_task.id = "task-args"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="DFLY-5678",
            branch_prefix="bugfix",
            workflow_name="fix-bug",
        )

        call_kwargs = mock_run_background.call_args[1]
        assert call_kwargs["args"] == {
            "issue_key": "DFLY-5678",
            "branch_prefix": "bugfix",
            "workflow_name": "fix-bug",
            "branch_name": None,
            "use_existing_branch": False,
        }


# =============================================================================
# Branch Name Generation Tests
# =============================================================================


class TestGenerateWorkflowBranchName:
    """Tests for generate_workflow_branch_name function."""

    def test_task_issue_type(self):
        """Test branch name generation for Task issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-1234",
            issue_type="Task",
            workflow_name="create-task",
        )
        assert result == "task/DFLY-1234/create-task"

    def test_epic_issue_type(self):
        """Test branch name generation for Epic issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-5678",
            issue_type="Epic",
            workflow_name="create-epic",
        )
        assert result == "epic/DFLY-5678/create-epic"

    def test_bug_issue_type(self):
        """Test branch name generation for Bug issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-9999",
            issue_type="Bug",
            workflow_name="create-bug",
        )
        assert result == "bug/DFLY-9999/create-bug"

    def test_story_issue_type(self):
        """Test branch name generation for Story issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-1111",
            issue_type="Story",
            workflow_name="create-story",
        )
        assert result == "story/DFLY-1111/create-story"

    def test_subtask_with_parent_key(self):
        """Test branch name generation for Sub-task with parent key."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-2222",
            issue_type="Sub-task",
            workflow_name="create-subtask",
            parent_key="DFLY-1000",
        )
        assert result == "subtask/DFLY-1000/DFLY-2222/create-subtask"

    def test_subtask_without_parent_key(self):
        """Test branch name for Sub-task without parent key (edge case)."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-3333",
            issue_type="Sub-task",
            workflow_name="create-subtask",
        )
        # Without parent key, should fall back to standard pattern
        assert result == "subtask/DFLY-3333/create-subtask"

    def test_case_insensitive_issue_type(self):
        """Test that issue type matching is case-insensitive."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-4444",
            issue_type="TASK",
            workflow_name="create-task",
        )
        assert result == "task/DFLY-4444/create-task"

    def test_unknown_issue_type_uses_type_name(self):
        """Test that unknown issue types use their lowercased name as prefix."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-5555",
            issue_type="Spike",
            workflow_name="some-workflow",
        )
        # Custom types use the type name lowercased
        assert result == "spike/DFLY-5555/create-spike"

    def test_update_workflow_uses_update_action(self):
        """Test branch name with update workflow uses update action."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-6666",
            issue_type="Task",
            workflow_name="update-task",
        )
        assert result == "task/DFLY-6666/update-task"

    def test_sub_task_with_hyphen(self):
        """Test branch name for 'Sub-task' issue type (with hyphen)."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-7777",
            issue_type="Sub-task",
            workflow_name="create-subtask",
            parent_key="DFLY-7000",
        )
        assert result == "subtask/DFLY-7000/DFLY-7777/create-subtask"

    def test_improvement_issue_type(self):
        """Test branch name generation for Improvement issue type."""
        result = generate_workflow_branch_name(
            issue_key="DFLY-8888",
            issue_type="Improvement",
            workflow_name="create-improvement",
        )
        assert result == "improvement/DFLY-8888/create-improvement"
