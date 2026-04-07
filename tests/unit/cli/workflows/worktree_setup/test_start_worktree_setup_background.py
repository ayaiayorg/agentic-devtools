"""Tests for StartWorktreeSetupBackground."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import (
    start_worktree_setup_background,
)


class TestStartWorktreeSetupBackground:
    """Tests for start_worktree_setup_background function."""

    @pytest.fixture(autouse=True)
    def _isolate_state(self):
        """Patch get_value and delete_value so tests never touch the real state file."""
        with (
            patch("agentic_devtools.state.get_value", return_value=None),
            patch("agentic_devtools.state.delete_value") as mock_delete,
        ):
            self._mock_delete_value = mock_delete
            yield

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_starts_background_task_with_basic_params(self, mock_run_background, mock_set_value):
        """Test starting background task with basic parameters."""
        mock_task = MagicMock()
        mock_task.id = "task-123"
        mock_run_background.return_value = mock_task

        result = start_worktree_setup_background(
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        assert result == "task-123"
        mock_run_background.assert_called_once()
        call_kwargs = mock_run_background.call_args[1]
        assert call_kwargs["module_path"] == "agentic_devtools.cli.workflows.worktree_setup"
        assert call_kwargs["function_name"] == "_setup_worktree_from_state"
        assert "agdt-setup-worktree-background" in call_kwargs["command_display_name"]
        assert "--issue-key PROJECT-1234" in call_kwargs["command_display_name"]

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_includes_user_request_when_provided(self, mock_run_background, mock_set_value):
        """Test that user_request is stored in state when provided."""
        mock_task = MagicMock()
        mock_task.id = "task-456"
        mock_run_background.return_value = mock_task

        result = start_worktree_setup_background(
            issue_key="PROJECT-1234",
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
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
            additional_params={"parent_key": "PROJECT-1000"},
        )

        assert result == "task-789"
        # Verify additional_params was stored in state as JSON
        import json

        expected_json = json.dumps({"parent_key": "PROJECT-1000"})
        mock_set_value.assert_any_call("worktree_setup.additional_params", expected_json)

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_basic_params_in_state(self, mock_run_background, mock_set_value):
        """Test that basic params are stored in state."""
        mock_task = MagicMock()
        mock_task.id = "task-esc"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
        )

        # Verify basic params were stored in state
        mock_set_value.assert_any_call("worktree_setup.issue_key", "PROJECT-1234")
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
            issue_key="PROJECT-5678",
            branch_prefix="bugfix",
            workflow_name="fix-bug",
        )

        call_kwargs = mock_run_background.call_args[1]
        assert call_kwargs["args"] == {
            "issue_key": "PROJECT-5678",
            "branch_prefix": "bugfix",
            "workflow_name": "fix-bug",
            "branch_name": None,
            "use_existing_branch": False,
        }

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_auto_execute_command_in_state_when_provided(self, mock_run_background, mock_set_value):
        """Test that auto_execute_command is stored in state as JSON when provided."""
        mock_task = MagicMock()
        mock_task.id = "task-cmd"
        mock_run_background.return_value = mock_task

        import json

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pr-id", "99"],
        )

        expected_json = json.dumps(["agdt-initiate-pull-request-review-workflow", "--pr-id", "99"])
        mock_set_value.assert_any_call("worktree_setup.auto_execute_command", expected_json)

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_auto_execute_timeout_when_non_default(self, mock_run_background, mock_set_value):
        """Test that auto_execute_timeout is stored in state when not the default."""
        mock_task = MagicMock()
        mock_task.id = "task-timeout"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["cmd"],
            auto_execute_timeout=120,
        )

        mock_set_value.assert_any_call("worktree_setup.auto_execute_timeout", "120")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_deletes_auto_execute_command_when_none(self, mock_run_background, mock_set_value):
        """Test that auto_execute_command is explicitly deleted when None to prevent stale leaks."""
        mock_task = MagicMock()
        mock_task.id = "task-no-cmd"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=None,
        )

        stored_keys = [call[0][0] for call in mock_set_value.call_args_list]
        assert "worktree_setup.auto_execute_command" not in stored_keys
        self._mock_delete_value.assert_any_call("worktree_setup.auto_execute_command")
        # Timeout is always persisted (even the default 60s) to prevent stale leaks
        mock_set_value.assert_any_call("worktree_setup.auto_execute_timeout", "60")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_timeout_when_default_60(self, mock_run_background, mock_set_value):
        """Test that auto_execute_timeout=60 is always persisted to prevent stale leaks."""
        mock_task = MagicMock()
        mock_task.id = "task-default-timeout"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["cmd"],
            auto_execute_timeout=60,
        )

        mock_set_value.assert_any_call("worktree_setup.auto_execute_timeout", "60")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_interactive_false_in_state(self, mock_run_background, mock_set_value):
        """Test that interactive=False is stored in state."""
        mock_task = MagicMock()
        mock_task.id = "task-interactive"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            interactive=False,
        )

        mock_set_value.assert_any_call("worktree_setup.interactive", "false")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_stores_interactive_true_to_override_prior_false(self, mock_run_background, mock_set_value):
        """Test that interactive=True is stored as 'true' to override any prior 'false' value."""
        mock_task = MagicMock()
        mock_task.id = "task-interactive-default"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            interactive=True,
        )

        mock_set_value.assert_any_call("worktree_setup.interactive", "true")

    @patch("agentic_devtools.state.get_value")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_captures_copilot_model_from_state(self, mock_run_background, mock_set_value, mock_get_value):
        """Test that copilot.model_id is captured and stored as worktree_setup.model."""
        mock_task = MagicMock()
        mock_task.id = "task-model"
        mock_run_background.return_value = mock_task
        mock_get_value.return_value = "claude-3.5-sonnet"

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        mock_get_value.assert_called_once_with("copilot.model_id")
        mock_set_value.assert_any_call("worktree_setup.model", "claude-3.5-sonnet")

    @patch("agentic_devtools.state.get_value")
    @patch("agentic_devtools.state.delete_value")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_does_not_store_model_when_absent(
        self, mock_run_background, mock_set_value, mock_delete_value, mock_get_value
    ):
        """Test that worktree_setup.model is cleared when copilot.model_id is absent."""
        mock_task = MagicMock()
        mock_task.id = "task-no-model"
        mock_run_background.return_value = mock_task
        mock_get_value.return_value = None

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        stored_keys = [call[0][0] for call in mock_set_value.call_args_list]
        assert "worktree_setup.model" not in stored_keys
        mock_delete_value.assert_any_call("worktree_setup.model")

    @patch("agentic_devtools.state.get_value")
    @patch("agentic_devtools.state.delete_value")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_does_not_store_model_when_whitespace_only(
        self, mock_run_background, mock_set_value, mock_delete_value, mock_get_value
    ):
        """Test that worktree_setup.model is cleared when copilot.model_id is whitespace-only."""
        mock_task = MagicMock()
        mock_task.id = "task-ws-model"
        mock_run_background.return_value = mock_task
        mock_get_value.return_value = "  "

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
        )

        stored_keys = [call[0][0] for call in mock_set_value.call_args_list]
        assert "worktree_setup.model" not in stored_keys
        mock_delete_value.assert_any_call("worktree_setup.model")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_explicit_model_param_takes_precedence_over_state(self, mock_run_background, mock_set_value):
        """Test that an explicit model parameter is stored instead of copilot.model_id from state."""
        mock_task = MagicMock()
        mock_task.id = "task-explicit-model"
        mock_run_background.return_value = mock_task

        start_worktree_setup_background(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            model="gpt-4o",
        )

        mock_set_value.assert_any_call("worktree_setup.model", "gpt-4o")

    def test_auto_execute_timeout_default_is_60(self):
        """Verify the default value of auto_execute_timeout is 60 via signature inspection."""
        import inspect

        sig = inspect.signature(start_worktree_setup_background)
        default = sig.parameters["auto_execute_timeout"].default
        assert default == 60
