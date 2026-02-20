"""Tests for InitiateWorkflow."""

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


class TestInitiateWorkflow:
    """Tests for initiate_workflow function."""

    def test_initiate_workflow_success(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test successful workflow initiation."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "Working on PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup state
        state.set_value("pull_request_id", "123")

        # Initiate workflow
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=[],
        )

        # Verify workflow state
        workflow = state.get_workflow_state()
        assert workflow is not None
        assert workflow["active"] == "pull-request-review"
        assert workflow["status"] == "initiated"
        assert workflow["step"] == "initiate"

        # Verify output
        captured = capsys.readouterr()
        assert "Working on PR #123" in captured.out

    def test_initiate_workflow_missing_required_state(self, temp_state_dir, temp_prompts_dir, clear_state_before):
        """Test workflow initiation fails with missing required state."""
        # Setup template in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "Template {{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Don't set required state
        with pytest.raises(SystemExit) as exc_info:
            base.initiate_workflow(
                workflow_name="pull-request-review",
                required_state_keys=["pull_request_id"],
                optional_state_keys=[],
            )
        assert exc_info.value.code == 1

    def test_initiate_workflow_with_optional_state(
        self, temp_state_dir, temp_prompts_dir, temp_output_dir, clear_state_before, capsys
    ):
        """Test workflow initiation with optional state."""
        # Setup template with optional variable in workflow subfolder
        workflow_dir = temp_prompts_dir / "pull-request-review"
        workflow_dir.mkdir()
        template = "PR #{{pull_request_id}}"
        template_file = workflow_dir / "default-initiate-prompt.md"
        template_file.write_text(template, encoding="utf-8")

        # Setup required state only
        state.set_value("pull_request_id", "123")

        # Initiate workflow - should succeed even without optional state
        base.initiate_workflow(
            workflow_name="pull-request-review",
            required_state_keys=["pull_request_id"],
            optional_state_keys=["jira.issue_key"],
        )

        captured = capsys.readouterr()
        assert "PR #123" in captured.out
