"""Tests for SetupWorktreeEnvironment."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    WorktreeSetupResult,
    setup_worktree_environment,
)

_INJECT_GIT = "agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings"
_INJECT_PYTHON = "agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings"


class TestSetupWorktreeEnvironment:
    """Tests for setup_worktree_environment function."""

    @patch(_INJECT_GIT)
    @patch(_INJECT_PYTHON)
    @patch("agentic_devtools.cli.workflows.worktree_setup.run_worktree_setup_script")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_full_setup_success(self, mock_create, mock_vscode, mock_script, mock_inject_python, mock_inject_git):
        """Test successful full environment setup."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_vscode.return_value = True

        result = setup_worktree_environment(
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            open_vscode=True,
        )

        assert result.success is True
        assert result.worktree_path == "/repos/PROJECT-1234"
        assert result.branch_name == "feature/PROJECT-1234/implementation"
        assert result.vscode_opened is True
        mock_script.assert_called_once_with("/repos/PROJECT-1234")
        mock_inject_git.assert_called_once_with("/repos/PROJECT-1234")

    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_setup_fails_when_worktree_fails(self, mock_create):
        """Test setup failure when worktree creation fails."""
        mock_create.return_value = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Git error",
        )

        result = setup_worktree_environment(issue_key="PROJECT-1234")

        assert result.success is False
        assert "Git error" in result.error_message

    @patch(_INJECT_GIT)
    @patch(_INJECT_PYTHON)
    @patch("agentic_devtools.cli.workflows.worktree_setup.run_worktree_setup_script")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_setup_without_vscode(self, mock_create, mock_vscode, mock_script, mock_inject_python, mock_inject_git):
        """Test setup without opening VS Code."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )

        result = setup_worktree_environment(
            issue_key="PROJECT-1234",
            open_vscode=False,
        )

        assert result.success is True
        assert result.vscode_opened is False
        mock_vscode.assert_not_called()
        mock_script.assert_called_once_with("/repos/PROJECT-1234")
        mock_inject_git.assert_called_once_with("/repos/PROJECT-1234")

    @patch(_INJECT_GIT)
    @patch(_INJECT_PYTHON)
    @patch("agentic_devtools.cli.workflows.worktree_setup.run_worktree_setup_script")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace", return_value=False)
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_vscode_opened_is_false_when_vscode_unavailable(
        self, mock_create, mock_vscode, mock_script, mock_inject_python, mock_inject_git
    ):
        """Test that vscode_opened is False when VS Code is not available."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )

        result = setup_worktree_environment(
            issue_key="PROJECT-1234",
            open_vscode=True,
        )

        assert result.success is True
        assert result.vscode_opened is False
        mock_inject_git.assert_called_once_with("/repos/PROJECT-1234")

    @patch(_INJECT_PYTHON)
    @patch(_INJECT_GIT)
    @patch("agentic_devtools.cli.workflows.worktree_setup.run_worktree_setup_script")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_inject_python_path_settings_called_with_worktree_path(
        self, mock_create, mock_vscode, mock_script, mock_inject_git, mock_inject_python
    ):
        """inject_python_path_settings is called with the worktree path on success."""
        mock_create.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_vscode.return_value = True

        setup_worktree_environment(issue_key="PROJECT-1234", open_vscode=True)

        mock_inject_python.assert_called_once_with("/repos/PROJECT-1234")

    @patch(_INJECT_PYTHON)
    @patch(_INJECT_GIT)
    @patch("agentic_devtools.cli.workflows.worktree_setup.create_worktree")
    def test_inject_python_path_settings_not_called_when_worktree_fails(
        self, mock_create, mock_inject_git, mock_inject_python
    ):
        """inject_python_path_settings is NOT called when worktree creation fails."""
        mock_create.return_value = WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Git error",
        )

        setup_worktree_environment(issue_key="PROJECT-1234")

        mock_inject_python.assert_not_called()
