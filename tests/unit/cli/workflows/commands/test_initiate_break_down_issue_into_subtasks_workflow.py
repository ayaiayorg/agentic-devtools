"""Tests for initiate_break_down_issue_into_subtasks_workflow."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands


class TestInitiateBreakDownIssueIntoSubtasksWorkflowBranches:
    """Tests for initiate_break_down_issue_into_subtasks_workflow branches."""

    def test_missing_issue_key_exits_with_error(self, temp_state_dir, clear_state_before, capsys):
        """Test error when issue_key is missing."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_break_down_issue_into_subtasks_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--issue-key is required" in captured.out

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.user_request", "Split into 3 subtasks")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_break_down_issue_into_subtasks_workflow(_argv=["--issue-key", "PROJECT-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Worktree setup started" in captured.out

        # Verify auto_execute_command includes --user-request
        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--user-request" in auto_cmd
        assert "Split into 3 subtasks" in auto_cmd
        assert "--skip-copilot-session" in auto_cmd

    def test_model_parsed_from_cli(self, temp_state_dir, clear_state_before, capsys):
        """--model CLI arg overrides the default model."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_break_down_issue_into_subtasks_workflow(
                    _argv=["--issue-key", "PROJECT-1234", "--model", "gpt-4"]
                )

        assert state.get_value("copilot.model_id") == "gpt-4"

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_break_down_issue_into_subtasks_workflow(_argv=["--issue-key", "PROJECT-1234"])
                assert exc_info.value.code == 1


class TestProgrammaticParamsSkipCliOverride:
    """Tests that programmatic params skip the CLI arg override branches."""

    def test_issue_key_and_user_request_set_programmatically(self, temp_state_dir, clear_state_before, capsys):
        """When issue_key and user_request are set programmatically,
        the `if X is None:` CLI override branches are skipped."""
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_break_down_issue_into_subtasks_workflow(
                    issue_key="PROJECT-1234",
                    user_request="Split into 3 subtasks",
                )

        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--issue-key" in auto_cmd
        assert "PROJECT-1234" in auto_cmd
        assert "--user-request" in auto_cmd
        assert "Split into 3 subtasks" in auto_cmd


class TestInitiateBreakDownIssueInteractive:
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
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_break_down_issue_into_subtasks_workflow(
                    _argv=["--issue-key", "PROJECT-1234", "--interactive", "true"]
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
                issue_key="PROJECT-1234",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_break_down_issue_into_subtasks_workflow(_argv=["--issue-key", "PROJECT-1234"])

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
        workflow_dir = temp_prompts_dir / "break-down-issue-into-subtasks"
        workflow_dir.mkdir()
        template = "Breaking down issue {{jira_issue_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("jira.issue_key", "PROJECT-1234")

        # Mock preflight to pass
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1234",
                branch_name="feature/PROJECT-1234/breakdown",
                issue_key="PROJECT-1234",
            )

            commands.initiate_break_down_issue_into_subtasks_workflow(_argv=["--issue-key", "PROJECT-1234"])

        # Verify workflow state was set
        workflow = state.get_workflow_state()
        assert workflow["active"] == "break-down-issue-into-subtasks"

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
        workflow_dir = temp_prompts_dir / "break-down-issue-into-subtasks"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(
            "Breaking down issue {{jira_issue_key}}", encoding="utf-8"
        )
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1234",
                branch_name="feature/PROJECT-1234/breakdown",
                issue_key="PROJECT-1234",
            )

            commands.initiate_break_down_issue_into_subtasks_workflow(
                _argv=["--issue-key", "PROJECT-1234", "--interactive", "true"]
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
        workflow_dir = temp_prompts_dir / "break-down-issue-into-subtasks"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(
            "Breaking down issue {{jira_issue_key}}", encoding="utf-8"
        )
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1234",
                branch_name="feature/PROJECT-1234/breakdown",
                issue_key="PROJECT-1234",
            )

            commands.initiate_break_down_issue_into_subtasks_workflow(_argv=["--issue-key", "PROJECT-1234"])

        assert state.get_value("workflow.context.interactive") == "false"


class TestStateDirShiftBreakDownIssue:
    """Tests for the state-dir shift guard in initiate_break_down_issue_into_subtasks_workflow."""

    def test_state_dir_shift_triggers_second_issue_key_write(
        self,
        temp_state_dir,
        clear_state_before,
        mock_workflow_state_clearing,
    ):
        """Test that when get_state_dir() changes after set_value, the key is re-written.

        Simulates the bootstrap-race where set_value("jira.issue_key", ...) lazily
        initialises runtime-bootstrap.json and shifts get_state_dir() to a scoped path.
        The guard must detect this and re-write the key to the new state directory.
        """
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        # Keep a reference to the real implementation so our mock can delegate to it.
        original_set_value = state.set_value

        shifted_dir = temp_state_dir / "shifted"
        shifted_dir.mkdir()

        # Simulate get_state_dir() returning a different directory after the first write.
        with patch(
            "agentic_devtools.cli.workflows.commands.get_state_dir",
            side_effect=[temp_state_dir, shifted_dir],
        ):
            # Ensure state.set_value() itself also sees the directory shift.
            call_count = {"n": 0}

            def _state_get_state_dir_side_effect():
                # Return the original temp_state_dir for the first "cycle" (load + save
                # of a single set_value() call), then return shifted_dir for all
                # subsequent calls to simulate the bootstrap scope shift happening
                # between separate set_value() calls, not mid-call.
                if call_count["n"] < 2:
                    dir_path = temp_state_dir
                else:
                    dir_path = shifted_dir
                call_count["n"] += 1
                return dir_path

            with patch(
                "agentic_devtools.state.get_state_dir",
                side_effect=_state_get_state_dir_side_effect,
            ):
                with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                    mock_pf.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="PROJECT-1234",
                        branch_name="feature/PROJECT-1234/breakdown",
                        issue_key="PROJECT-1234",
                    )
                    with patch("agentic_devtools.cli.workflows.commands.initiate_workflow") as mock_iw:
                        with patch("agentic_devtools.state.update_workflow_context"):
                            # Wrap state.set_value so we can assert how often jira.issue_key is written,
                            # while still executing the real implementation.
                            with patch("agentic_devtools.state.set_value") as mock_set_value:

                                def _set_value_side_effect(*args, **kwargs):
                                    return original_set_value(*args, **kwargs)

                                mock_set_value.side_effect = _set_value_side_effect

                                commands.initiate_break_down_issue_into_subtasks_workflow(
                                    _argv=["--issue-key", "PROJECT-1234"]
                                )

        # initiate_workflow should have been called (function completed successfully)
        mock_iw.assert_called_once()

        # The guard should have caused at least a second write of jira.issue_key (before and
        # after the state-dir shift). Additional writes (e.g. initial CLI persist) are allowed.
        jira_issue_key_calls = [
            call for call in mock_set_value.call_args_list if call.args and call.args[0] == "jira.issue_key"
        ]
        assert len(jira_issue_key_calls) >= 2

        shifted_state_file = shifted_dir / "state.json"
        assert shifted_state_file.exists()


class TestSkipCopilotSession:
    """Tests for the --skip-copilot-session flag."""

    def test_skip_copilot_session_accepted_without_error(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """--skip-copilot-session is accepted (future-proofing for when session launch is wired)."""
        workflow_dir = temp_prompts_dir / "break-down-issue-into-subtasks"
        workflow_dir.mkdir()
        (workflow_dir / "default-initiate-prompt.md").write_text(
            "Breaking down issue {{jira_issue_key}}", encoding="utf-8"
        )
        state.set_value("jira.issue_key", "PROJECT-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="PROJECT-1234",
                branch_name="feature/PROJECT-1234/breakdown",
                issue_key="PROJECT-1234",
            )

            commands.initiate_break_down_issue_into_subtasks_workflow(
                _argv=["--issue-key", "PROJECT-1234", "--skip-copilot-session"]
            )

        workflow = state.get_workflow_state()
        assert workflow["active"] == "break-down-issue-into-subtasks"
