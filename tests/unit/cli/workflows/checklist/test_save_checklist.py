"""Tests for SaveChecklist."""

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import (
    Checklist,
    ChecklistItem,
    save_checklist,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestSaveChecklist:
    """Tests for save_checklist function."""

    def test_save_to_workflow(self, temp_state_dir, clear_state_before):
        """Test saving checklist to workflow state."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )
        checklist = Checklist(items=[ChecklistItem(id=1, text="Task")])
        save_checklist(checklist)

        # Verify it was saved
        workflow = state.get_workflow_state()
        assert "checklist" in workflow["context"]
        assert workflow["context"]["checklist"]["items"][0]["text"] == "Task"

    def test_save_preserves_other_context(self, temp_state_dir, clear_state_before):
        """Test saving checklist preserves other context keys."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234", "branch_name": "feature/test"},
        )
        checklist = Checklist()
        save_checklist(checklist)

        workflow = state.get_workflow_state()
        assert workflow["context"]["jira_issue_key"] == "DFLY-1234"
        assert workflow["context"]["branch_name"] == "feature/test"

    def test_save_no_workflow_raises(self, temp_state_dir, clear_state_before):
        """Test saving without workflow raises error."""
        checklist = Checklist()
        with pytest.raises(ValueError, match="No active workflow"):
            save_checklist(checklist)
