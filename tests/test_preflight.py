"""Tests for pre-flight checks."""

from pathlib import Path
from unittest.mock import patch

from dfly_ai_helpers.cli.workflows.preflight import (
    PreflightResult,
    check_worktree_and_branch,
    generate_setup_instructions,
    get_current_git_branch,
    get_git_repo_root,
    perform_auto_setup,
)


class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_passed_when_both_valid(self):
        """Test that passed is True when both checks pass."""
        result = PreflightResult(
            folder_valid=True,
            branch_valid=True,
            folder_name="DFLY-1850",
            branch_name="feature/DFLY-1850/test",
            issue_key="DFLY-1850",
        )
        assert result.passed is True

    def test_passed_when_folder_invalid(self):
        """Test that passed is False when folder check fails."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=True,
            folder_name="some-folder",
            branch_name="feature/DFLY-1850/test",
            issue_key="DFLY-1850",
        )
        assert result.passed is False

    def test_passed_when_branch_invalid(self):
        """Test that passed is False when branch check fails."""
        result = PreflightResult(
            folder_valid=True,
            branch_valid=False,
            folder_name="DFLY-1850",
            branch_name="main",
            issue_key="DFLY-1850",
        )
        assert result.passed is False

    def test_failure_reasons_both_invalid(self):
        """Test failure reasons when both checks fail."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="some-folder",
            branch_name="main",
            issue_key="DFLY-1850",
        )
        reasons = result.failure_reasons
        assert len(reasons) == 2
        assert "Folder" in reasons[0]
        assert "Branch" in reasons[1]

    def test_failure_reasons_no_branch(self):
        """Test failure reasons when no branch is checked out."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="some-folder",
            branch_name="",
            issue_key="DFLY-1850",
        )
        reasons = result.failure_reasons
        assert "Not in a git repository" in reasons[1]


class TestGetCurrentGitBranch:
    """Tests for get_current_git_branch function."""

    def test_returns_branch_name(self):
        """Test that it returns the branch name on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "feature/DFLY-1234/test\n"

            result = get_current_git_branch()
            assert result == "feature/DFLY-1234/test"

    def test_returns_none_on_failure(self):
        """Test that it returns None on subprocess failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1

            result = get_current_git_branch()
            assert result is None

    def test_returns_none_on_empty_output(self):
        """Test that it returns None when no branch (detached HEAD)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""

            result = get_current_git_branch()
            assert result is None

    def test_handles_file_not_found(self):
        """Test that it handles git not being installed."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = get_current_git_branch()
            assert result is None


class TestGetGitRepoRoot:
    """Tests for get_git_repo_root function."""

    def test_returns_repo_root(self):
        """Test that it returns the repo root path."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "/home/user/repos/my-repo\n"

            result = get_git_repo_root()
            assert result == "/home/user/repos/my-repo"

    def test_returns_none_on_failure(self):
        """Test that it returns None outside a git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 128

            result = get_git_repo_root()
            assert result is None


class TestCheckWorktreeAndBranch:
    """Tests for check_worktree_and_branch function."""

    def test_both_valid_case_insensitive(self):
        """Test that checking is case-insensitive."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/dfly-1850")
            mock_branch.return_value = "feature/DFLY-1850/test"
            mock_root.return_value = "/repos/dfly-1850"

            result = check_worktree_and_branch("DFLY-1850")

            assert result.folder_valid is True
            assert result.branch_valid is True
            assert result.passed is True

    def test_folder_contains_key(self):
        """Test that folder containing the key passes."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/my-DFLY-1850-work")
            mock_branch.return_value = "feature/DFLY-1850/work"
            mock_root.return_value = "/repos/my-DFLY-1850-work"

            result = check_worktree_and_branch("DFLY-1850")

            assert result.folder_valid is True

    def test_branch_missing(self):
        """Test when no branch is checked out."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/DFLY-1850")
            mock_branch.return_value = None
            mock_root.return_value = None

            result = check_worktree_and_branch("DFLY-1850")

            assert result.branch_valid is False

    def test_source_branch_match_for_pr_review_without_jira(self):
        """Test that branch validation passes when source_branch matches current branch.

        This is critical for PR review workflows without a Jira issue key, where
        the folder is PR{id} but the branch is the actual PR source branch.
        """
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/PR24031")
            mock_branch.return_value = "feature/dfly-test-file-source-file-param"
            mock_root.return_value = "/repos/PR24031"

            # issue_key is PR24031 (folder matches) but branch doesn't contain PR24031
            # However, source_branch matches so it should pass
            result = check_worktree_and_branch(
                "PR24031",
                source_branch="feature/dfly-test-file-source-file-param",
            )

            assert result.folder_valid is True
            assert result.branch_valid is True
            assert result.matched_by_source_branch is True
            assert result.passed is True

    def test_source_branch_match_with_refs_heads_prefix(self):
        """Test that source_branch normalization handles refs/heads/ prefix."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/PR12345")
            mock_branch.return_value = "feature/my-branch"
            mock_root.return_value = "/repos/PR12345"

            # source_branch has refs/heads/ prefix from Azure DevOps API
            result = check_worktree_and_branch(
                "PR12345",
                source_branch="refs/heads/feature/my-branch",
            )

            assert result.branch_valid is True
            assert result.matched_by_source_branch is True

    def test_source_branch_no_match_when_different(self):
        """Test that source_branch doesn't match when branches are different."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/PR24031")
            mock_branch.return_value = "main"
            mock_root.return_value = "/repos/PR24031"

            result = check_worktree_and_branch(
                "PR24031",
                source_branch="feature/different-branch",
            )

            assert result.folder_valid is True
            assert result.branch_valid is False  # Branch doesn't match
            assert result.matched_by_source_branch is False

    def test_issue_key_match_preferred_over_source_branch(self):
        """Test that issue_key in branch is used when available, not source_branch match."""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "dfly_ai_helpers.cli.workflows.preflight.get_current_git_branch"
        ) as mock_branch, patch("dfly_ai_helpers.cli.workflows.preflight.get_git_repo_root") as mock_root:
            mock_cwd.return_value = Path("/repos/DFLY-1850")
            mock_branch.return_value = "feature/DFLY-1850/my-work"
            mock_root.return_value = "/repos/DFLY-1850"

            result = check_worktree_and_branch(
                "DFLY-1850",
                source_branch="feature/some-other-branch",
            )

            # Branch contains issue key so matched_by_source_branch should be False
            assert result.branch_valid is True
            assert result.matched_by_source_branch is False


class TestGenerateSetupInstructions:
    """Tests for generate_setup_instructions function."""

    def test_includes_failure_reasons(self):
        """Test that failure reasons are included."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="wrong-folder",
            branch_name="main",
            issue_key="DFLY-1850",
        )

        instructions = generate_setup_instructions("DFLY-1850", result)

        assert "DFLY-1850" in instructions
        assert "Issues Detected" in instructions

    def test_includes_worktree_command_when_folder_wrong(self):
        """Test that worktree command is included when folder is wrong."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=True,
            folder_name="wrong-folder",
            branch_name="feature/DFLY-1850/test",
            issue_key="DFLY-1850",
        )

        instructions = generate_setup_instructions("DFLY-1850", result)

        assert "git worktree add" in instructions
        assert "DFLY-1850" in instructions

    def test_includes_branch_command_when_only_branch_wrong(self):
        """Test that branch command is included when only branch is wrong."""
        result = PreflightResult(
            folder_valid=True,
            branch_valid=False,
            folder_name="DFLY-1850",
            branch_name="main",
            issue_key="DFLY-1850",
        )

        instructions = generate_setup_instructions("DFLY-1850", result)

        assert "git switch -c" in instructions
        assert "feature/DFLY-1850" in instructions

    def test_includes_vscode_command(self):
        """Test that VS Code open command is included."""
        result = PreflightResult(
            folder_valid=False,
            branch_valid=False,
            folder_name="wrong",
            branch_name="main",
            issue_key="DFLY-1850",
        )

        instructions = generate_setup_instructions("DFLY-1850", result)

        assert "code .." in instructions
        assert "dfly-platform-management.code-workspace" in instructions


class TestPerformAutoSetup:
    """Tests for perform_auto_setup function."""

    @patch("dfly_ai_helpers.cli.workflows.worktree_setup.start_worktree_setup_background")
    def test_starts_background_task_successfully(self, mock_start_background, capsys):
        """Test successful background task start."""
        mock_start_background.return_value = "task-12345"

        result = perform_auto_setup(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        assert result is True
        mock_start_background.assert_called_once_with(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            branch_name=None,
            use_existing_branch=False,
            workflow_name="work-on-jira-issue",
            user_request=None,
            additional_params=None,
        )
        captured = capsys.readouterr()
        assert "task-12345" in captured.out
        assert "Background task started" in captured.out

    @patch("dfly_ai_helpers.cli.workflows.worktree_setup.start_worktree_setup_background")
    def test_passes_user_request_to_background(self, mock_start_background, capsys):
        """Test that user_request is passed to background task."""
        mock_start_background.return_value = "task-67890"

        perform_auto_setup(
            issue_key="DFLY-5678",
            branch_prefix="bugfix",
            workflow_name="create-jira-issue",
            user_request="Create a new feature for testing",
        )

        mock_start_background.assert_called_once()
        call_kwargs = mock_start_background.call_args[1]
        assert call_kwargs["user_request"] == "Create a new feature for testing"

    @patch("dfly_ai_helpers.cli.workflows.worktree_setup.start_worktree_setup_background")
    def test_passes_additional_params_to_background(self, mock_start_background, capsys):
        """Test that additional_params are passed to background task."""
        mock_start_background.return_value = "task-abc"

        perform_auto_setup(
            issue_key="DFLY-9999",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
            additional_params={"parent_key": "DFLY-1000"},
        )

        mock_start_background.assert_called_once()
        call_kwargs = mock_start_background.call_args[1]
        assert call_kwargs["additional_params"] == {"parent_key": "DFLY-1000"}

    @patch("dfly_ai_helpers.cli.workflows.worktree_setup.start_worktree_setup_background")
    def test_handles_exception_gracefully(self, mock_start_background, capsys):
        """Test that exceptions are caught and return False."""
        mock_start_background.side_effect = Exception("Connection failed")

        result = perform_auto_setup(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Failed to start background task" in captured.out
        assert "Connection failed" in captured.out

    @patch("dfly_ai_helpers.cli.workflows.worktree_setup.start_worktree_setup_background")
    def test_prints_next_steps_instructions(self, mock_start_background, capsys):
        """Test that next steps instructions are printed."""
        mock_start_background.return_value = "task-xyz"

        perform_auto_setup(
            issue_key="DFLY-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        captured = capsys.readouterr()
        assert "NEXT STEPS" in captured.out
        assert "dfly-task-log" in captured.out
        assert "dfly-task-wait" in captured.out
