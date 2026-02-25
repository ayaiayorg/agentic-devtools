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

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_command_runs_after_new_worktree_created(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
    ):
        """Test that auto_execute_command is run after new worktree creation."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["agdt-review", "--pr-id", "42"],
            auto_execute_timeout=120,
        )

        mock_run_cmd.assert_called_once_with(
            ["agdt-review", "--pr-id", "42"],
            "/repos/DFLY-1234",
            120,
        )
        mock_set_value.assert_any_call("worktree_setup.auto_execute_exit_code", "0")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_command_runs_for_existing_worktree(
        self,
        mock_check_exists,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
    ):
        """Test that auto_execute_command is run when worktree already exists."""
        mock_check_exists.return_value = "/repos/DFLY-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["agdt-review"],
        )

        mock_run_cmd.assert_called_once_with(["agdt-review"], "/repos/DFLY-1234", 300)
        mock_set_value.assert_any_call("worktree_setup.auto_execute_exit_code", "0")

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_failure_continues_setup(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        capsys,
    ):
        """Test that setup continues even when auto_execute_command fails."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 1  # Non-zero exit code

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["failing-cmd"],
        )

        # Setup should complete normally despite command failure
        captured = capsys.readouterr()
        assert "Environment setup complete!" in captured.out
        mock_set_value.assert_any_call("worktree_setup.auto_execute_exit_code", "1")

    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_no_auto_execute_when_command_not_provided(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
    ):
        """Test that _run_auto_execute_command is not called when auto_execute_command is None."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        with patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command") as mock_run_cmd:
            setup_worktree_in_background_sync(
                issue_key="DFLY-1234",
                workflow_name="work-on-jira-issue",
                auto_execute_command=None,
            )

        mock_run_cmd.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_for_pr_review_workflow(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_copilot,
    ):
        """Test that Copilot session is started for pull-request-review workflow with auto_execute."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "99"],
            interactive=True,
        )

        mock_copilot.assert_called_once_with("/repos/DFLY-1234", interactive=True)

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_not_started_for_non_pr_review_workflow(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_copilot,
    ):
        """Test that Copilot session is NOT started for non-PR-review workflows."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/impl",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["agdt-some-command"],
        )

        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_not_started_when_no_auto_execute(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_copilot,
    ):
        """Test that Copilot session is NOT started when auto_execute_command is None."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            auto_execute_command=None,
        )

        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_for_existing_pr_review_worktree(
        self,
        mock_check_exists,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_copilot,
    ):
        """Test that Copilot session is started when worktree already exists for PR review."""
        mock_check_exists.return_value = "/repos/DFLY-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "42"],
            interactive=False,
        )

        mock_copilot.assert_called_once_with("/repos/DFLY-1234", interactive=False)
