"""Tests for TestInitiateCreateJiraSubtaskWorkflowBranches."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


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
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    This is needed because workflow initiation commands clear all state at the start,
    but tests set up state before calling the command. Without this mock, the test's
    state setup would be wiped immediately.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield


class TestInitiateCreateJiraSubtaskWorkflowBranches:
    """Test additional branches in initiate_create_jira_subtask_workflow."""

    def test_preflight_fails_and_auto_setup_succeeds(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails but auto-setup succeeds (returns early)."""
        state.set_value("jira.issue_key", "DFLY-1235")
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = True
                commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-1235"])

        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_preflight_fails_and_auto_setup_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when preflight fails and auto-setup also fails."""
        state.set_value("jira.issue_key", "DFLY-1235")
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_pf:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_pf.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong",
                branch_name="main",
                issue_key="DFLY-1235",
            )

            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_setup:
                mock_setup.return_value = False
                with pytest.raises(SystemExit) as exc_info:
                    commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-1235"])
                assert exc_info.value.code == 1

    def test_no_issue_key_no_parent_key_error(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key and no parent_key, shows error."""
        with pytest.raises(SystemExit) as exc_info:
            commands.initiate_create_jira_subtask_workflow(_argv=[])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--parent-key is required" in captured.out

    def test_no_issue_key_creates_placeholder(self, temp_state_dir, clear_state_before, capsys):
        """Test when no issue_key but parent_key provided, creates placeholder."""
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (True, "DFLY-1235")
            commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "DFLY-1234"])

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["issue_type"] == "Sub-task"
        assert call_kwargs["parent_key"] == "DFLY-1234"
        captured = capsys.readouterr()
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_no_issue_key_placeholder_creation_fails(self, temp_state_dir, clear_state_before, capsys):
        """Test when placeholder creation fails."""
        state.set_value("jira.parent_key", "DFLY-1234")

        with patch(
            "agentic_devtools.cli.workflows.worktree_setup.create_placeholder_and_setup_worktree"
        ) as mock_create:
            mock_create.return_value = (False, None)
            with pytest.raises(SystemExit) as exc_info:
                commands.initiate_create_jira_subtask_workflow(_argv=["--parent-key", "DFLY-1234"])
            assert exc_info.value.code == 1


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_create_jira_subtask_workflow(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test create jira subtask workflow command with continuation (issue key already provided)."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "create-jira-subtask"
        workflow_dir.mkdir()
        template = "Creating subtask for {{jira_parent_key}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state - simulate continuation after placeholder creation
        state.set_value("jira.parent_key", "DFLY-1234")
        state.set_value("jira.issue_key", "DFLY-1235")  # Provided issue key means continuation

        # Mock preflight to pass (we're already in correct context)
        with patch("agentic_devtools.cli.workflows.preflight.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1235",
                branch_name="feature/DFLY-1234/DFLY-1235/implementation",
                issue_key="DFLY-1235",
            )

            # Execute command with issue-key (continuation mode)
            commands.initiate_create_jira_subtask_workflow(_argv=["--issue-key", "DFLY-1235"])

        # Verify
        workflow = state.get_workflow_state()
        assert workflow["active"] == "create-jira-subtask"
