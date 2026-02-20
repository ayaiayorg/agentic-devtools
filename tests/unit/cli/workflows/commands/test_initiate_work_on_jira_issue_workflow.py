"""Tests for initiate_work_on_jira_issue_workflow."""

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


class TestWorkflowCommands:
    """Tests for individual workflow command functions."""

    def test_work_on_jira_issue_workflow_preflight_fail(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test work on jira issue workflow command when pre-flight fails triggers auto-setup."""
        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")

        # Mock pre-flight to fail (folder doesn't contain issue key)
        # Patch at commands module level where it's imported at top
        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=False,
                branch_valid=False,
                folder_name="wrong-folder",
                branch_name="main",
                issue_key="DFLY-1234",
            )

            # Mock perform_auto_setup to prevent actual worktree creation
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                mock_auto_setup.return_value = True  # Setup successful

                # Execute command
                commands.initiate_work_on_jira_issue_workflow(_argv=[])

        # Verify - auto-setup was called and workflow returns for continuation in new VS Code
        mock_auto_setup.assert_called_once()
        captured = capsys.readouterr()
        assert "Not in the correct context" in captured.out
        assert "continue the workflow in the new VS Code window" in captured.out

    def test_work_on_jira_issue_workflow_preflight_pass(
        self,
        temp_state_dir,
        temp_prompts_dir,
        temp_output_dir,
        clear_state_before,
        mock_workflow_state_clearing,
        capsys,
    ):
        """Test work on jira issue workflow command when pre-flight passes."""
        # Setup template for planning step in workflow subfolder
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template = "Planning work for {{issue_key}}: {{issue_summary}}"
        template_file = workflow_dir / "default-planning-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("jira.issue_key", "DFLY-1234")
        # Mock the issue data that would be fetched
        state.set_value(
            "jira.last_issue",
            {
                "fields": {
                    "summary": "Test issue",
                    "issuetype": {"name": "Task"},
                    "labels": ["backend"],
                    "description": "Test description",
                    "comment": {"comments": []},
                }
            },
        )

        # Mock pre-flight to pass (patch at commands module level where it's imported at top)
        with patch("agentic_devtools.cli.workflows.commands.check_worktree_and_branch") as mock_preflight:
            from agentic_devtools.cli.workflows.preflight import PreflightResult

            mock_preflight.return_value = PreflightResult(
                folder_valid=True,
                branch_valid=True,
                folder_name="DFLY-1234",
                branch_name="feature/DFLY-1234/test",
                issue_key="DFLY-1234",
            )

            # Also mock perform_auto_setup to prevent any actual subprocess calls
            with patch("agentic_devtools.cli.workflows.preflight.perform_auto_setup") as mock_auto_setup:
                mock_auto_setup.return_value = True

                # Mock subprocess.run for the dfly-get-jira-issue call
                with patch("subprocess.run") as mock_subprocess:
                    mock_subprocess.return_value.returncode = 0

                    # Execute command
                    commands.initiate_work_on_jira_issue_workflow(_argv=[])

        # Verify - should be in planning step
        workflow = state.get_workflow_state()
        assert workflow["active"] == "work-on-jira-issue"
        assert workflow["step"] == "planning"
        captured = capsys.readouterr()
        assert "Planning work for DFLY-1234" in captured.out
