"""Tests for TestInitiateUpdateJiraIssueWorkflowBranches."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_prompts_dir(tmp_path):
    """Create a temporary prompts directory with test templates."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    with patch.object(loader, "get_prompts_dir", return_value=prompts_dir):
        yield prompts_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "temp"
    output_dir.mkdir()
    with patch.object(loader, "get_temp_output_dir", return_value=output_dir):
        yield output_dir


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test.

    Note: We only remove the state file, not the entire temp folder,
    to avoid deleting directories created by other fixtures (like temp_prompts_dir).
    """
    state_file = temp_state_dir / "state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation and _ensure_bootstrap_identity to be no-ops.

    Workflow initiation commands resolve bootstrap identity and reset workflow
    tracking keys (workflow, agdt_run_id) at the start.  This fixture prevents
    both operations, which is useful when tests pre-set workflow state before
    calling the command and want to avoid real filesystem/git operations.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity"):
            with patch("agentic_devtools.cli.workflows.commands._ensure_bootstrap_identity_and_scope"):
                yield


class TestInitiateUpdateJiraIssueWorkflowBranches:
    """Test additional branches in initiate_update_jira_issue_workflow."""

    def test_missing_issue_key_error(self, temp_state_dir, clear_state_before, capsys):
        """Test error when issue_key is missing."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_update_jira_issue_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--issue-key is required" in captured.out

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.user_request", "Update the description")

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
                commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "Copilot session will start automatically" in captured.out

        # Verify auto_execute_command includes --user-request
        call_kwargs = mock_setup.call_args[1]
        auto_cmd = call_kwargs["auto_execute_command"]
        assert "--user-request" in auto_cmd
        assert "Update the description" in auto_cmd

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
                    commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])
                assert exc_info.value.code == 1


class TestInitiateUpdateJiraIssueInteractive:
    """Tests for the --interactive flag behaviour."""

    def test_interactive_true_parsed_from_cli(self, temp_state_dir, clear_state_before, capsys):
        """Test that --interactive true enables interactive mode."""
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
                commands.initiate_update_jira_issue_workflow(
                    _argv=["--issue-key", "DFLY-1234", "--interactive", "true"]
                )

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is True

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
                commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        call_kwargs = mock_setup.call_args[1]
        assert call_kwargs["interactive"] is False


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_update_jira_issue_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test update jira issue workflow command with continuation (already in correct context)."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "update-jira-issue"
        workflow_dir.mkdir()
        template = "Updating issue {{jira_issue_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")

        # Mock preflight to pass (we're already in correct context)
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/implementation",
                issue_key="DFLY-1234",
            )

            # Mock session launcher to avoid waiting for prompt file
            with patch("agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_update_jira_issue"):
                # Execute command with issue-key
                commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "update-jira-issue"


class TestStateDirShiftUpdateJiraIssue:
    """Tests for the state-dir shift guard in initiate_update_jira_issue_workflow."""

    def test_state_dir_shift_triggers_second_issue_key_write(
        self,
        temp_state_dir,
        clear_state_before,
        mock_workflow_state_clearing,
    ):
        """Test that when get_state_dir() changes after set_value, the issue key is written
        to the final state directory.

        Simulates the bootstrap race where set_value("jira.issue_key", ...) runs before
        runtime-bootstrap.json exists, and a subsequent get_state_dir() call resolves to
        a different, scoped path. The guard must detect this change and re-write the key
        into the new state-dir so the workflow sees a consistent jira.issue_key value.
        """
        from agentic_devtools.cli.workflows.preflight import PreflightResult

        shifted_dir = temp_state_dir / "shifted"
        shifted_dir.mkdir()

        with patch(
            "agentic_devtools.cli.workflows.commands.get_state_dir",
            side_effect=[temp_state_dir, shifted_dir],
        ):
            call_count = {"n": 0}

            def _state_get_state_dir_side_effect():
                # First two calls (one load + one save) use the original temp_state_dir.
                # Subsequent calls use shifted_dir to simulate the bootstrap shift
                # happening between separate set_value() calls, not mid-call.
                call_count["n"] += 1
                if call_count["n"] <= 2:
                    return temp_state_dir
                return shifted_dir

            with (
                patch(
                    "agentic_devtools.state.get_state_dir",
                    side_effect=_state_get_state_dir_side_effect,
                ),
                patch(
                    "agentic_devtools.state.set_value",
                    wraps=state.set_value,
                ) as mock_set_value,
            ):
                with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
                    mock_pf.return_value = PreflightResult(
                        folder_valid=True,
                        branch_valid=True,
                        folder_name="DFLY-1234",
                        branch_name="feature/DFLY-1234/impl",
                        issue_key="DFLY-1234",
                    )
                    with patch("agentic_devtools.cli.workflows.commands.initiate_workflow") as mock_iw:
                        with patch(
                            "agentic_devtools.cli.workflows.worktree_setup._start_copilot_session_for_update_jira_issue"
                        ):
                            commands.initiate_update_jira_issue_workflow(_argv=["--issue-key", "DFLY-1234"])

        # initiate_workflow should have been called (function completed successfully)
        mock_iw.assert_called_once()

        # set_value should have been called twice for jira.issue_key
        jira_issue_key_calls = [
            call for call in mock_set_value.call_args_list if call.args and call.args[0] == "jira.issue_key"
        ]
        assert len(jira_issue_key_calls) >= 2

        # The shifted state file must exist, proving at least one write landed in
        # the final resolved state directory after the shift.
        shifted_state_file = shifted_dir / "state.json"
        assert shifted_state_file.exists()
