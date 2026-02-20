"""Tests for SetupWorktreeInBackgroundSync."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import (
    WorktreeSetupResult,
    setup_worktree_in_background_sync,
)


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
