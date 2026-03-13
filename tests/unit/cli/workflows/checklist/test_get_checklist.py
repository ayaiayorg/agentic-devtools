"""Tests for GetChecklist."""

import json

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import (
    get_checklist,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestGetChecklist:
    """Tests for get_checklist function."""

    def test_no_workflow(self, temp_state_dir, clear_state_before):
        """Test returns None when no workflow active."""
        result = get_checklist()
        assert result is None

    def test_no_checklist_in_workflow(self, temp_state_dir, clear_state_before):
        """Test returns None when workflow has no checklist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={},
        )
        result = get_checklist()
        assert result is None

    def test_returns_checklist(self, temp_state_dir, clear_state_before):
        """Test returns checklist from workflow state."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "checklist": {
                    "items": [{"id": 1, "text": "Task", "completed": False}],
                    "modified_by_agent": False,
                }
            },
        )
        result = get_checklist()
        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].text == "Task"

    def test_reads_from_file_first(self, temp_state_dir, clear_state_before):
        """Test that get_checklist reads from file before workflow context."""
        # Write to file
        file_dir = temp_state_dir / "implementations"
        file_dir.mkdir()
        file_data = {
            "items": [{"id": 1, "text": "File task", "completed": True}],
            "modified_by_agent": True,
        }
        (file_dir / "checklist.json").write_text(json.dumps(file_data), encoding="utf-8")

        # Also set in workflow context with different data
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "checklist": {
                    "items": [{"id": 1, "text": "Context task", "completed": False}],
                    "modified_by_agent": False,
                }
            },
        )

        result = get_checklist()
        assert result is not None
        # Should read from file, not context
        assert result.items[0].text == "File task"
        assert result.items[0].completed is True
        assert result.modified_by_agent is True

    def test_falls_back_to_context_when_file_invalid(self, temp_state_dir, clear_state_before):
        """Test fallback to workflow context when file contains invalid JSON."""
        file_dir = temp_state_dir / "implementations"
        file_dir.mkdir()
        (file_dir / "checklist.json").write_text("not json", encoding="utf-8")

        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "checklist": {
                    "items": [{"id": 1, "text": "Context task", "completed": False}],
                    "modified_by_agent": False,
                }
            },
        )

        result = get_checklist()
        assert result is not None
        assert result.items[0].text == "Context task"
