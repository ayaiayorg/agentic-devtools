"""Tests for SetupWorktreeEnvironment."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    WorktreeSetupResult,
    setup_worktree_environment,
)


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

    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace", return_value=False)
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_vscode_opened_is_false_when_vscode_unavailable(self, mock_create, mock_vscode):
        """Test that vscode_opened is False when VS Code is not available."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )

        result = setup_worktree_environment(
            issue_key="DFLY-1234",
            open_vscode=True,
        )

        assert result.success is True
        assert result.vscode_opened is False
