"""Tests for SetupWorktreeInBackgroundSync.

Copilot session-triggering decision tree
-----------------------------------------
The function ``setup_worktree_in_background_sync`` prepares the worktree and
VS Code environment according to the following rules. It never starts a
Copilot session directly; any Copilot startup is handled by VS Code tasks
(for example, an ``agdt-copilot-auto-start`` task) configured elsewhere.

1. ``auto_execute_command`` is truthy (for example, a non-empty list)
   a. Run ``_run_auto_execute_command()`` **first** (before injecting the VS Code
      auto-start task and before opening VS Code), so that all workflow context
      data (PR details, Jira issue, etc.) is available when VS Code's
      ``folderOpen`` event fires the ``agdt-copilot-auto-start`` task.
   b. ``_maybe_inject_auto_start_before_vscode()`` is called after auto-execute.
   c. ``open_vscode_workspace()`` is called last.
   d. No Copilot session helper is called directly from this function; the
      auto-start task injected in step (b) is responsible for any session
      startup, regardless of the exit code from ``_run_auto_execute_command()``.

2. ``auto_execute_command`` is falsy (for example, ``None`` or an empty string)
   a. ``_maybe_inject_auto_start_before_vscode()`` is called first.
   b. ``open_vscode_workspace()`` is called next.
   c. As in case (1), this function does **not** start any Copilot sessions
      directly.

3. Non-PR-review workflows (``workflow_name != "pull-request-review"``)
   This helper still only manages the worktree and VS Code workspace; Copilot
   sessions, if any, are orchestrated by external tooling and not by this
   function.
"""

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
    def test_copilot_session_not_started_for_pr_review_workflow_with_auto_execute(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_copilot,
    ):
        """Test that Copilot session is NOT started when auto_execute_command re-runs the workflow (new worktree)."""
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

        mock_copilot.assert_not_called()

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
    def test_copilot_session_not_started_for_existing_pr_review_worktree_with_auto_execute(
        self,
        mock_check_exists,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_copilot,
    ):
        """Test that Copilot session is NOT started when auto_execute re-runs the workflow (existing worktree)."""
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

        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.setup_worktree_environment")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_not_started_when_auto_execute_fails_new_worktree(
        self,
        mock_check_exists,
        mock_setup,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_copilot,
    ):
        """Test that Copilot session is NOT started when auto_execute fails (new worktree)."""
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/review",
        )
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 1  # Non-zero exit code

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "99"],
            interactive=True,
        )

        mock_copilot.assert_not_called()

    @patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_pr_review")
    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_copilot_session_not_started_when_auto_execute_fails_existing_worktree(
        self,
        mock_check_exists,
        mock_open_vscode,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_set_value,
        mock_copilot,
    ):
        """Test that Copilot session is NOT started when auto_execute fails (existing worktree)."""
        mock_check_exists.return_value = "/repos/DFLY-1234"
        mock_open_vscode.return_value = True
        mock_continuation_prompt.return_value = "Continue..."
        mock_ai_prompt.return_value = "AI Agent prompt"
        mock_run_cmd.return_value = 1  # Non-zero exit code

        setup_worktree_in_background_sync(
            issue_key="DFLY-1234",
            workflow_name="pull-request-review",
            auto_execute_command=["agdt-initiate-pull-request-review-workflow", "--pull-request-id", "42"],
            interactive=True,
        )

        mock_copilot.assert_not_called()

    @patch("agentic_devtools.state.set_value")
    @patch("agentic_devtools.cli.workflows.worktree_setup.open_vscode_workspace")
    @patch("agentic_devtools.cli.workflows.worktree_setup._run_auto_execute_command")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_ai_agent_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.get_worktree_continuation_prompt")
    @patch("agentic_devtools.cli.workflows.worktree_setup.check_worktree_exists")
    def test_auto_execute_runs_before_vscode_opens_existing_worktree(
        self,
        mock_check_exists,
        mock_continuation_prompt,
        mock_ai_prompt,
        mock_run_cmd,
        mock_open_vscode,
        mock_set_value,
    ):
        """Verify _run_auto_execute_command is called before open_vscode_workspace (existing worktree).

        This ensures that when VS Code's folderOpen event fires the
        agdt-copilot-auto-start task, all workflow context data has already
        been fetched by _run_auto_execute_command.
        """
        mock_check_exists.return_value = "/repos/DFLY-1234"
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
            mock_inject_auto_start.side_effect = (
                lambda *a, **kw: call_order.append("inject_auto_start") or None
            )

            setup_worktree_in_background_sync(
                issue_key="DFLY-1234",
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
    ):
        """Verify _run_auto_execute_command is called before open_vscode_workspace (new worktree).

        This ensures that when VS Code's folderOpen event fires the
        agdt-copilot-auto-start task, all workflow context data has already
        been fetched by _run_auto_execute_command.
        """
        mock_check_exists.return_value = None
        mock_setup.return_value = WorktreeSetupResult(
            success=True,
            worktree_path="/repos/DFLY-1234",
            branch_name="feature/DFLY-1234/implementation",
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
            mock_inject_auto_start.side_effect = (
                lambda *a, **kw: call_order.append("inject_auto_start") or None
            )

            setup_worktree_in_background_sync(
                issue_key="DFLY-1234",
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
