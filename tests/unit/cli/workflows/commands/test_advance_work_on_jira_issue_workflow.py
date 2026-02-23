"""Tests for AdvanceWorkOnJiraIssueWorkflow."""

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


class TestAdvanceWorkOnJiraIssueWorkflow:
    """Tests for advance_work_on_jira_issue_workflow function."""

    def test_advance_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when workflow is not active."""
        with pytest.raises(SystemExit) as exc_info:
            commands.advance_work_on_jira_issue_workflow()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "work-on-jira-issue workflow is not active" in captured.err

    def test_advance_no_workflow_state(self, temp_state_dir, clear_state_before, capsys):
        """Test advance fails when get_workflow_state returns None."""
        with patch("agentic_devtools.state.is_workflow_active", return_value=True):
            with patch("agentic_devtools.state.get_workflow_state", return_value=None):
                with pytest.raises(SystemExit) as exc_info:
                    commands.advance_work_on_jira_issue_workflow()
                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "Could not get workflow state" in captured.err

    def test_advance_auto_detects_next_step(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance auto-detects next step from step_order."""
        # Set up workflow in planning step
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={
                "jira_issue_key": "DFLY-1234",
                "branch_name": "feature/DFLY-1234/test",
                "issue_summary": "Test issue",
            },
        )

        # Create template for checklist-creation step
        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-checklist-creation-prompt.md"
        template_file.write_text("Checklist creation for {{issue_key}}", encoding="utf-8")

        commands.advance_work_on_jira_issue_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "checklist-creation"

    def test_advance_defaults_to_implementation_on_unknown_step(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance defaults to implementation when current step not in order."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="unknown-step",
            context={"jira_issue_key": "DFLY-1234"},
        )

        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-implementation-prompt.md"
        template_file.write_text("Implementation for {{issue_key}}", encoding="utf-8")

        commands.advance_work_on_jira_issue_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "implementation"

    def test_advance_to_completion_step(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test advance to completion step sets status to completed."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="pull-request",
            context={
                "jira_issue_key": "DFLY-1234",
                "branch_name": "feature/DFLY-1234/test",
                "pull_request_url": "https://example.com/pr/123",
            },
        )
        state.set_value("pull_request_id", "123")

        workflow_dir = temp_prompts_dir / "work-on-jira-issue"
        workflow_dir.mkdir()
        template_file = workflow_dir / "default-completion-prompt.md"
        template_file.write_text("Workflow complete for {{issue_key}}", encoding="utf-8")

        commands.advance_work_on_jira_issue_workflow()

        workflow = state.get_workflow_state()
        assert workflow["step"] == "completion"
        assert workflow["status"] == "completed"
