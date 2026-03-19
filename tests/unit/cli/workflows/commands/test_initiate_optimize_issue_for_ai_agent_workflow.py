"""Tests for initiate_optimize_issue_for_ai_agent_workflow."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands


class TestInitiateOptimizeIssueForAiAgentWorkflowBranches:
    """Tests for initiate_optimize_issue_for_ai_agent_workflow branches."""

    def test_missing_issue_key_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Test error when issue_key is missing."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--issue-key is required" in captured.out

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.user_request", "Focus on acceptance criteria")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Worktree setup started" in captured.out

        # Verify auto_execute_command includes --user-request
        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--user-request" in auto_cmd
        assert "Focus on acceptance criteria" in auto_cmd

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-1234"])
                assert exc_info.value.code == 1


class TestInitiateOptimizeIssueInteractive:
    """Tests for the --interactive flag behaviour."""

    def test_auto_execute_command_includes_interactive(self, temp_state_dir, clear_state_before, capsys):
        """Test that auto_execute_command includes --interactive when set."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_optimize_issue_for_ai_agent_workflow(
                    _argv=["--issue-key", "DFLY-1234", "--interactive", "true"]
                )

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--interactive" in auto_cmd
        assert "true" in auto_cmd

    def test_interactive_defaults_to_false(self, temp_state_dir, clear_state_before, capsys):
        """Test that interactive defaults to False when not specified."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-1234"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False


class TestWorkflowCommands:
    """Tests for the workflow command preflight-pass path."""

    def test_preflight_passes_initiates_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test that when preflight passes, initiate_workflow is called with the right name."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "optimize-issue-for-ai-agent"
        workflow_dir.mkdir()
        template = "Optimizing issue {{jira_issue_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")

        # Mock preflight to pass
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/optimize",
                issue_key="DFLY-1234",
            )

            commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-1234"])

        # Verify workflow state was set
        workflow = state.get_workflow_state()
        assert workflow["active"] == "optimize-issue-for-ai-agent"

    def test_preflight_passes_persists_interactive_to_state(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test that interactive is persisted to workflow.interactive in state on preflight pass."""
        workflow_dir = temp_prompts_dir / "optimize-issue-for-ai-agent"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(
            "Optimizing issue {{jira_issue_key}}", encoding="utf-8"
        )
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/optimize",
                issue_key="DFLY-1234",
            )

            commands.initiate_optimize_issue_for_ai_agent_workflow(
                _argv=["--issue-key", "DFLY-1234", "--interactive", "true"]
            )

        assert state.get_value("workflow.context.interactive") == "true"

    def test_preflight_passes_persists_interactive_false_by_default(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test that interactive defaults to false and is stored in state."""
        workflow_dir = temp_prompts_dir / "optimize-issue-for-ai-agent"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(
            "Optimizing issue {{jira_issue_key}}", encoding="utf-8"
        )
        state.set_value("jira.issue_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/optimize",
                issue_key="DFLY-1234",
            )

            commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-1234"])

        assert state.get_value("workflow.context.interactive") == "false"


class TestIssueKeyWriteGuardOptimize:
    """Tests for the issue-key write guard in initiate_optimize_issue_for_ai_agent_workflow."""

    def test_issue_key_write_guard_triggers_when_current_differs(
        self,
        temp_state_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Exercise the write guard when current_issue_key != resolved_issue_key.

        Simulates the bootstrap-missing scenario by mocking set_value as a no-op so the
        initial write does not persist to state. A subsequent get_value therefore returns
        None, making current_issue_key != resolved_issue_key True and causing the guarded
        set_value call to execute.
        """
        from unittest.mock import call as mock_call

        from agentic_devtools.cli.workflows.preflight import PreflightResult

        with patch("agentic_devtools.state.set_value") as mock_set_value:
            with patch("agentic_devtools.cli.workflows.commands.initiate_workflow"):
                with patch("agentic_devtools.state.update_workflow_context"):
                    with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                        mock_pf.return_value = PreflightResult(
                            folder_valid=True,
                            branch_valid=True,
                            folder_name="DFLY-1234",
                            branch_name="feature/DFLY-1234/optimize",
                            issue_key="DFLY-1234",
                        )
                        commands.initiate_optimize_issue_for_ai_agent_workflow(_argv=["--issue-key", "DFLY-1234"])

        # set_value("jira.issue_key", "DFLY-1234") must be called at least twice:
        # once for the initial persist and once inside the write guard.
        issue_key_calls = [c for c in mock_set_value.call_args_list if c == mock_call("jira.issue_key", "DFLY-1234")]
        assert len(issue_key_calls) >= 2, (
            f"Expected set_value('jira.issue_key', ...) called ≥2 times, got {issue_key_calls}"
        )
