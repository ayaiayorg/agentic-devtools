"""Tests for SetupWorktreeInBackgroundSync.

Copilot session-triggering decision tree
-----------------------------------------
The function ``setup_worktree_in_background_sync`` prepares the worktree and
VS Code environment.  After ``open_vscode_workspace()`` returns, it calls
``_start_copilot_session_for_workflow()`` as a secondary fallback mechanism
when the ``workflow_name`` is found in ``_WORKFLOW_PROMPT_FILENAMES``.

1. ``auto_execute_command`` is truthy (for example, a non-empty list)
   a. Run ``_run_auto_execute_command()`` **first** (before injecting the VS Code
      auto-start task and before opening VS Code), so that all workflow context
      data (PR details, Jira issue, etc.) is available when VS Code's
      ``folderOpen`` event fires the ``agdt-copilot-auto-start`` task.
   b. ``_maybe_inject_auto_start_before_vscode()`` is called after auto-execute.
   c. ``open_vscode_workspace()`` is called next.
   d. ``_start_copilot_session_for_workflow()`` is called after VS Code opens
      (when the workflow name is in ``_WORKFLOW_PROMPT_FILENAMES``).

2. ``auto_execute_command`` is falsy (for example, ``None`` or an empty string)
   a. ``_maybe_inject_auto_start_before_vscode()`` is called first.
   b. ``open_vscode_workspace()`` is called next.
   c. ``_start_copilot_session_for_workflow()`` is called after VS Code opens
      (when the workflow name is in ``_WORKFLOW_PROMPT_FILENAMES``).

3. Unknown workflow names (not in ``_WORKFLOW_PROMPT_FILENAMES``)
   ``_start_copilot_session_for_workflow()`` is silently skipped.
"""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.workflows.worktree_setup import (
    WorktreeSetupResult,
    setup_worktree_in_background_sync,
)


class TestSetupWorktreeInBackgroundSync:
    """Tests for setup_worktree_in_background_sync function."""

    @pytest.fixture(autouse=True)
    def _mock_prompt_file_relative_path(self):
        """Auto-mock _prompt_file_relative_path for all tests.

        The function resolves state directories by chdir-ing into the
        worktree path, which does not exist in tests (paths like
        ``/repos/PROJECT-1234``).  Mocking it avoids ``FileNotFoundError``
        while still allowing the new ``_start_copilot_session_for_workflow``
        call to be tested via its own mock.
        """
        with patch(
            "agentic_devtools.cli.workflows.worktree_setup._prompt_file_relative_path",
            return_value=".agdt/workflows/_test/_test/temp-prompt.md",
        ):
            yield

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_task_permission_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_existing_worktree_reuses_and_opens(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_inject_task,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_start_session,
        capsys,
    ):
        """Test that existing worktree is reused, PATH settings injected, and VS Code opened."""
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        mock_check_exists.assert_called_once_with("PROJECT-1234")
        mock_inject_git.assert_called_once_with("/repos/PROJECT-1234")
        mock_inject_python.assert_called_once_with("/repos/PROJECT-1234")
        mock_inject_task.assert_called_once_with("/repos/PROJECT-1234")
        mock_open_vscode.assert_called_once_with("/repos/PROJECT-1234")
        captured = capsys.readouterr()
        assert "Worktree already exists" in captured.out
        assert "Environment ready!" in captured.out

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
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
        mock_start_session,
        capsys,
    ):
        """Test that new worktree is created when none exists."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
            vscode_opened=True,
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            workflow_name="work-on-jira-issue",
        )

        mock_check_exists.assert_called_once_with("PROJECT-1234")
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
                issue_key="PROJECT-1234",
                branch_prefix="feature",
                workflow_name="work-on-jira-issue",
            )

        assert "Git worktree command failed" in str(exc_info.value)

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
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
        mock_start_session,
    ):
        """Test that user_request is passed to continuation prompt."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            branch_prefix="feature",
            workflow_name="create-jira-issue",
            user_request="Create a feature for X",
            additional_params={"parent_key": "PROJECT-1000"},
        )

        mock_continuation_prompt.assert_called_with(
            "PROJECT-1234",
            "create-jira-issue",
            "Create a feature for X",
            {"parent_key": "PROJECT-1000"},
        )

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
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
        mock_start_session,
    ):
        """Test that auto_execute_command is run after new worktree creation."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["agdt-review", "--pr-id", "42"],
            auto_execute_timeout=120,
        )

        mock_run_cmd.assert_called_once_with(
            ["agdt-review", "--pr-id", "42"],
            "/repos/PROJECT-1234",
            120,
        )
        mock_set_value.assert_any_call("worktree_setup.auto_execute_exit_code", "0")

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_task_permission_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_command_runs_for_existing_worktree(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_inject_task,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_start_session,
    ):
        """Test that auto_execute_command is run when worktree already exists."""
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["agdt-review"],
        )

        mock_run_cmd.assert_called_once_with(["agdt-review"], "/repos/PROJECT-1234", 60)
        mock_set_value.assert_any_call("worktree_setup.auto_execute_exit_code", "0")

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
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
        mock_start_session,
        capsys,
    ):
        """Test that setup continues even when auto_execute_command fails."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 1  # Non-zero exit code

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["failing-cmd"],
        )

        # Setup should complete normally despite command failure
        captured = capsys.readouterr()
        assert "Environment setup complete!" in captured.out
        mock_set_value.assert_any_call("worktree_setup.auto_execute_exit_code", "1")

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
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
        mock_start_session,
    ):
        """Test that _run_auto_execute_command is not called when auto_execute_command is None."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        with patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command") as mock_run_cmd:
            setup_worktree_in_background_sync(
                issue_key="PROJECT-1234",
                workflow_name="work-on-jira-issue",
                auto_execute_command=None,
            )

        mock_run_cmd.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_for_pr_review_new_worktree(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow IS called for PR review (new worktree)."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "99"],
            interactive=True,
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["worktree_path"] == "/repos/PROJECT-1234"
        assert call_kwargs["workflow_name"] == "pull-request-review"
        assert call_kwargs["interactive"] is True

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_for_non_pr_review_known_workflow(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow IS called for known non-PR-review workflows."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/impl",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="work-on-jira-issue",
            auto_execute_command=["agdt-some-command"],
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["workflow_name"] == "work-on-jira-issue"

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_when_no_auto_execute(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow IS called even when auto_execute_command is None."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=None,
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["workflow_name"] == "pull-request-review"

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_task_permission_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_for_existing_pr_review_worktree(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_inject_task,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow IS called for existing PR review worktree."""
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 0

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "42"],
            interactive=False,
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["worktree_path"] == "/repos/PROJECT-1234"
        assert call_kwargs["workflow_name"] == "pull-request-review"
        assert call_kwargs["interactive"] is False

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_when_auto_execute_fails_new_worktree(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow IS called even when auto_execute fails (new worktree)."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 1  # Non-zero exit code

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "99"],
            interactive=True,
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["workflow_name"] == "pull-request-review"

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_task_permission_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_started_when_auto_execute_fails_existing_worktree(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_inject_task,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow IS called even when auto_execute fails (existing worktree)."""
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 1  # Non-zero exit code

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "42"],
            interactive=True,
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["worktree_path"] == "/repos/PROJECT-1234"
        assert call_kwargs["workflow_name"] == "pull-request-review"

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_task_permission_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_runs_before_vscode_opens_existing_worktree(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_inject_task,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_open_vscode,
        mock_set_value,
        mock_start_session,
    ):
        """Verify _run_auto_execute_command is called before open_vscode_workspace (existing worktree).

        This ensures that when VS Code's folderOpen event fires the
        agdt-copilot-auto-start task, all workflow context data has already
        been fetched by _run_auto_execute_command.
        """
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_open_vscode.return_value = True

        call_order: list[str] = []
        mock_run_cmd.side_effect = lambda *a, **kw: call_order.append("auto_execute") or 0
        mock_open_vscode.side_effect = lambda *a, **kw: call_order.append("open_vscode") or True

        # Patch _maybe_inject_auto_start_before_vscode so the test is deterministic
        # and to track that it is called between auto_execute and open_vscode.
        with patch(
            "agentic_devtools.cli.workflows.worktree_setup._maybe_inject_auto_start_before_vscode"
        ) as mock_inject_auto_start:
            mock_inject_auto_start.side_effect = lambda *a, **kw: call_order.append("inject_auto_start") or None

            setup_worktree_in_background_sync(
                issue_key="PROJECT-1234",
                workflow_name="work-on-jira-issue",
                auto_execute_command=["agdt-review", "--pr-id", "42"],
            )

        # Verify that all three steps ran and in the intended order:
        # auto_execute → inject_auto_start → open_vscode.
        assert "auto_execute" in call_order, "_run_auto_execute_command was not called"
        assert "inject_auto_start" in call_order, "_maybe_inject_auto_start_before_vscode was not called"
        assert "open_vscode" in call_order, "open_vscode_workspace was not called"
        assert call_order.index("auto_execute") < call_order.index("inject_auto_start"), (
            "_run_auto_execute_command must be called before _maybe_inject_auto_start_before_vscode"
        )
        assert call_order.index("inject_auto_start") < call_order.index("open_vscode"), (
            "_maybe_inject_auto_start_before_vscode must be called before open_vscode_workspace"
        )

        # Verify that a pre-generated run_id (12-char hex) is passed.
        import re

        _call_kwargs = mock_inject_auto_start.call_args[1]
        assert "run_id" in _call_kwargs, "run_id must be passed as a keyword argument"
        assert re.fullmatch(r"[0-9a-f]{12}", _call_kwargs["run_id"]), (
            f"run_id must be a 12-character hex string, got {_call_kwargs['run_id']!r}"
        )

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_runs_before_vscode_opens_new_worktree(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_open_vscode,
        mock_set_value,
        mock_start_session,
    ):
        """Verify _run_auto_execute_command is called before open_vscode_workspace (new worktree).

        This ensures that when VS Code's folderOpen event fires the
        agdt-copilot-auto-start task, all workflow context data has already
        been fetched by _run_auto_execute_command.
        """
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/implementation",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        call_order: list[str] = []
        mock_run_cmd.side_effect = lambda *a, **kw: call_order.append("auto_execute") or 0
        mock_open_vscode.side_effect = lambda *a, **kw: call_order.append("open_vscode") or True

        # Patch _maybe_inject_auto_start_before_vscode so the test is deterministic
        # and to track that it is called between auto_execute and open_vscode.
        with patch(
            "agentic_devtools.cli.workflows.worktree_setup._maybe_inject_auto_start_before_vscode"
        ) as mock_inject_auto_start:
            mock_inject_auto_start.side_effect = lambda *a, **kw: call_order.append("inject_auto_start") or None

            setup_worktree_in_background_sync(
                issue_key="PROJECT-1234",
                workflow_name="work-on-jira-issue",
                auto_execute_command=["agdt-review", "--pr-id", "42"],
            )

        # Verify that all three steps ran and in the intended order:
        # auto_execute → inject_auto_start → open_vscode.
        assert "auto_execute" in call_order, "_run_auto_execute_command was not called"
        assert "inject_auto_start" in call_order, "_maybe_inject_auto_start_before_vscode was not called"
        assert "open_vscode" in call_order, "open_vscode_workspace was not called"
        assert call_order.index("auto_execute") < call_order.index("inject_auto_start"), (
            "_run_auto_execute_command must be called before _maybe_inject_auto_start_before_vscode"
        )
        assert call_order.index("inject_auto_start") < call_order.index("open_vscode"), (
            "_maybe_inject_auto_start_before_vscode must be called before open_vscode_workspace"
        )

        # Verify that a pre-generated run_id (12-char hex) is passed.
        import re

        _call_kwargs = mock_inject_auto_start.call_args[1]
        assert "run_id" in _call_kwargs, "run_id must be passed as a keyword argument"
        assert re.fullmatch(r"[0-9a-f]{12}", _call_kwargs["run_id"]), (
            f"run_id must be a 12-character hex string, got {_call_kwargs['run_id']!r}"
        )

    def test_auto_execute_timeout_default_is_60(self):
        """Verify the default value of auto_execute_timeout is 60 via signature inspection."""
        import inspect

        sig = inspect.signature(setup_worktree_in_background_sync)
        default = sig.parameters["auto_execute_timeout"].default
        assert default == 60

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_not_started_for_unknown_workflow(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow is NOT called for unknown workflow names."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/impl",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="unknown-workflow",
        )

        mock_start_session.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_not_started_for_unknown_workflow_existing_worktree(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow is NOT called for unknown workflow (existing worktree)."""
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="unknown-workflow",
        )

        mock_start_session.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_python_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.inject_git_path_settings")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_called_after_vscode_opens_existing_worktree(
        self,
        mock_check_exists,
        mock_inject_git,
        mock_inject_python,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_open_vscode,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow is called AFTER open_vscode_workspace (existing worktree)."""
        mock_check_exists.return_value = "/repos/PROJECT-1234"
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        call_order: list[str] = []
        mock_open_vscode.side_effect = lambda *a, **kw: call_order.append("open_vscode") or True
        mock_start_session.side_effect = lambda **kw: call_order.append("start_session") or True

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
        )

        assert "open_vscode" in call_order, "open_vscode_workspace was not called"
        assert "start_session" in call_order, "_start_copilot_session_for_workflow was not called"
        assert call_order.index("open_vscode") < call_order.index("start_session"), (
            "_start_copilot_session_for_workflow must be called after open_vscode_workspace"
        )

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_called_after_vscode_opens_new_worktree(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_open_vscode,
        mock_start_session,
    ):
        """Test that _start_copilot_session_for_workflow is called AFTER open_vscode_workspace (new worktree)."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        call_order: list[str] = []
        mock_open_vscode.side_effect = lambda *a, **kw: call_order.append("open_vscode") or True
        mock_start_session.side_effect = lambda **kw: call_order.append("start_session") or True

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
        )

        assert "open_vscode" in call_order, "open_vscode_workspace was not called"
        assert "start_session" in call_order, "_start_copilot_session_for_workflow was not called"
        assert call_order.index("open_vscode") < call_order.index("start_session"), (
            "_start_copilot_session_for_workflow must be called after open_vscode_workspace"
        )

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_workflow")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_passes_model_through_new_worktree(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_start_session,
    ):
        """Test that model parameter is passed through to _start_copilot_session_for_workflow."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/PROJECT-1234",
            branch_name="feature/PROJECT-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"

        setup_worktree_in_background_sync(
            issue_key="PROJECT-1234",
            workflow_name="pull-request-review",
            model="claude-3.5-sonnet",
        )

        mock_start_session.assert_called_once()
        call_kwargs = mock_start_session.call_args[1]
        assert call_kwargs["model"] == "claude-3.5-sonnet"
