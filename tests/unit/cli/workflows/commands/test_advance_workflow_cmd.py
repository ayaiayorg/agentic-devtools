"""Tests for AdvanceWorkflowCmd."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
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


class TestAdvanceWorkflowCmd:
    """Tests for advance_workflow_cmd entry point."""

    def test_advance_workflow_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance workflow command when no workflow is active."""
        from agentic_devtools.cli.workflows import advance_workflow_cmd

        with pytest.raises(SystemExit) as exc_info:
            advance_workflow_cmd()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No workflow is currently active" in captured.err

    def test_advance_workflow_unsupported_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test advance workflow command with unsupported workflow type."""
        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(name="unsupported-workflow", status="active", step="step1")

        with pytest.raises(SystemExit) as exc_info:
            advance_workflow_cmd()
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "does not support manual advancement" in captured.err

    def test_advance_workflow_work_on_jira_issue(self, temp_state_dir, clear_state_before):
        """Test advance workflow command with work-on-jira-issue workflow."""
        import sys

        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="active",
            step="research",
            context={"jira_issue_key": "TEST-123"},
        )

        with patch.object(sys, "argv", ["agdt-advance-workflow"]):
            with patch("agentic_devtools.cli.workflows.advance_work_on_jira_issue_workflow") as mock_advance:
                advance_workflow_cmd()
                mock_advance.assert_called_once_with(None)

    def test_advance_workflow_pull_request_review(self, temp_state_dir, clear_state_before):
        """Test advance workflow command with pull-request-review workflow."""
        import sys

        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(
            name="pull-request-review",
            status="active",
            step="review",
            context={"pull_request_id": "456"},
        )

        with patch.object(sys, "argv", ["agdt-advance-workflow"]):
            with patch("agentic_devtools.cli.workflows.advance_pull_request_review_workflow") as mock_advance:
                advance_workflow_cmd()
                mock_advance.assert_called_once_with(None)

    def test_advance_workflow_with_step_argument(self, temp_state_dir, clear_state_before):
        """Test advance workflow command with explicit step argument."""
        import sys

        from agentic_devtools.cli.workflows import advance_workflow_cmd

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="active",
            step="research",
            context={"jira_issue_key": "TEST-123"},
        )

        with patch.object(sys, "argv", ["agdt-advance-workflow", "implement"]):
            with patch("agentic_devtools.cli.workflows.advance_work_on_jira_issue_workflow") as mock_advance:
                advance_workflow_cmd()
                mock_advance.assert_called_once_with("implement")
