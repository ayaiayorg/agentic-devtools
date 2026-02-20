"""Tests for MarkItemsCompleted."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import (
    mark_items_completed,
)


@pytest.fixture
def temp_state_dir(tmp_path):
    """Use a temporary directory for state storage."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestMarkItemsCompleted:
    """Tests for mark_items_completed function."""

    def test_marks_items(self, temp_state_dir, clear_state_before):
        """Test marking items complete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": False},
                        {"id": 2, "text": "Task 2", "completed": False},
                    ],
                    "modified_by_agent": False,
                }
            },
        )

        checklist, marked = mark_items_completed([1, 2])
        assert marked == [1, 2]
        assert checklist.items[0].completed is True
        assert checklist.items[1].completed is True

    def test_no_checklist_raises(self, temp_state_dir, clear_state_before):
        """Test marking without checklist raises error."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={},
        )
        with pytest.raises(ValueError, match="No checklist exists"):
            mark_items_completed([1])
