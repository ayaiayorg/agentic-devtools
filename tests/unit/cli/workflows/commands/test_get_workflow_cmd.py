"""Tests for WorkflowCLICommands."""

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


class TestWorkflowCLICommands:
    """Tests for workflow CLI commands in cli/state.py."""

    def test_get_workflow_cmd_no_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test get workflow command when no workflow is active."""
        from agentic_devtools.cli.state import get_workflow_cmd

        get_workflow_cmd()
        captured = capsys.readouterr()
        assert "No workflow is currently active" in captured.out

    def test_get_workflow_cmd_with_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test get workflow command when workflow is active."""
        from agentic_devtools.cli.state import get_workflow_cmd

        state.set_workflow_state(
            name="pull-request-review",
            status="active",
            step="initiate",
            context={"pull_request_id": "123"},
        )

        get_workflow_cmd()
        captured = capsys.readouterr()
        assert "pull-request-review" in captured.out
        assert "active" in captured.out
        assert "initiate" in captured.out

    def test_clear_workflow_cmd(self, temp_state_dir, clear_state_before, capsys):
        """Test clear workflow command."""
        from agentic_devtools.cli.state import clear_workflow_cmd

        state.set_workflow_state(name="test", status="active", step="step1")
        clear_workflow_cmd()

        assert state.get_workflow_state() is None
        captured = capsys.readouterr()
        assert "Workflow 'test' cleared" in captured.out
