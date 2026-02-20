"""Tests for StartWorktreeSetupBackground."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    start_worktree_setup_background,
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
