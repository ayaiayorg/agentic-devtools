"""Tests for AdvanceWorkflowStep."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import base
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


class TestAdvanceWorkflowStep:
    """Tests for advance_workflow_step function."""

    def test_advance_step_success(self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys):
        """Test successful step advancement."""
        # Setup initial workflow
        state.set_workflow_state(
            name="test-workflow",
            status="active",
            step="initiate",
            context={"key": "value"},
        )

        # Setup template for next step in workflow subfolder
        workflow_dir = temp_prompts_dir / "test-workflow"
        workflow_dir.mkdir()
        template = "Step 2 content"
        template_file = workflow_dir / "default-step2-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Advance step (requires workflow_name and step_name)
        base.advance_workflow_step("test-workflow", "step2")

        # Verify workflow state updated
        workflow = state.get_workflow_state()
        assert workflow["step"] == "step2"

        # Verify output
        captured = capsys.readouterr()
        assert "Step 2 content" in captured.out

    def test_advance_step_no_active_workflow(self, temp_state_dir, clear_state_before):
        """Test advancing step fails when no workflow is active."""
        with pytest.raises(SystemExit) as exc_info:
            base.advance_workflow_step("test-workflow", "step2")
        assert exc_info.value.code == 1
