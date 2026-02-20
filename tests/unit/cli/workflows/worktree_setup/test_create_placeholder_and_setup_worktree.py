"""Tests for CreatePlaceholderAndSetupWorktree."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.worktree_setup import (
    PlaceholderIssueResult,
    WorktreeSetupResult,
    create_placeholder_and_setup_worktree,
)


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
