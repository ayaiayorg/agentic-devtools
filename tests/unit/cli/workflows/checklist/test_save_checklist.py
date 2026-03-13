"""Tests for SaveChecklist."""

import json

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
    state_file = temp_state_dir / "state.json"
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

    def test_save_writes_to_implementations_file(self, temp_state_dir, clear_state_before):
        """Test that save_checklist writes to implementations/checklist.json."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={},
        )
        checklist = Checklist(items=[ChecklistItem(id=1, text="File task")])
        save_checklist(checklist)

        file_path = temp_state_dir / "implementations" / "checklist.json"
        assert file_path.exists()
        data = json.loads(file_path.read_text(encoding="utf-8"))
        assert data["items"][0]["text"] == "File task"

    def test_save_calls_mark_dirty(self, temp_state_dir, clear_state_before):
        """Test that save_checklist calls mark_dirty after writing."""
        from agentic_devtools.cli.git.agdt_branch import _reset_dirty, is_dirty

        _reset_dirty()
        try:
            state.set_workflow_state(
                name="work-on-jira-issue",
                status="in-progress",
                step="implementation",
                context={},
            )
            checklist = Checklist(items=[ChecklistItem(id=1, text="Task")])
            save_checklist(checklist)
            assert is_dirty() is True
        finally:
            _reset_dirty()

    def test_save_succeeds_when_mark_dirty_import_fails(self, temp_state_dir, clear_state_before):
        """Test that save still writes files when mark_dirty import fails."""
        import builtins
        from unittest.mock import patch

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if "agdt_branch" in name:
                raise ImportError("simulated")
            return original_import(name, *args, **kwargs)

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={},
        )
        checklist = Checklist(items=[ChecklistItem(id=1, text="Task")])
        with patch.object(builtins, "__import__", side_effect=failing_import):
            save_checklist(checklist)

        file_path = temp_state_dir / "implementations" / "checklist.json"
        assert file_path.exists()
