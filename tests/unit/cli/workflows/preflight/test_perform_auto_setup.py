"""Tests for PerformAutoSetup."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.preflight import (
    perform_auto_setup,
)


class TestPerformAutoSetup:
    """Tests for perform_auto_setup function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.start_worktree_setup_background")
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
            auto_execute_command=None,
            auto_execute_timeout=300,
        )
        captured = capsys.readouterr()
        assert "task-12345" in captured.out
        assert "Background task started" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.start_worktree_setup_background")
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

    @patch("agentic_devtools.cli.workflows.worktree_setup.start_worktree_setup_background")
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

    @patch("agentic_devtools.cli.workflows.worktree_setup.start_worktree_setup_background")
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

    @patch("agentic_devtools.cli.workflows.worktree_setup.start_worktree_setup_background")
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
        assert "agdt-task-log" in captured.out
        assert "agdt-task-wait" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup.start_worktree_setup_background")
    def test_passes_auto_execute_command_to_background(self, mock_start_background, capsys):
        """Test that auto_execute_command is passed through to the background task."""
        mock_start_background.return_value = "task-exec"

        perform_auto_setup(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pr-id", "99"],
            auto_execute_timeout=120,
        )

        mock_start_background.assert_called_once()
        call_kwargs = mock_start_background.call_args[1]
        assert call_kwargs["auto_execute_command"] == [
            "agdt-initiate-pull-request-review-workflow",
            "--pr-id",
            "99",
        ]
        assert call_kwargs["auto_execute_timeout"] == 120
