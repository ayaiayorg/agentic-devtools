"""Tests for InitializeChecklist."""

import pytest

from agentic_devtools.cli.workflows.checklist import (
    initialize_checklist,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestInitializeChecklist:
    """Tests for initialize_checklist function."""

    def test_creates_checklist_from_items(self):
        """Test creating checklist from item texts."""
        items = ["Task 1", "Task 2", "Task 3"]
        checklist = initialize_checklist(items)
        assert len(checklist.items) == 3
        assert checklist.items[0].id == 1
        assert checklist.items[0].text == "Task 1"
        assert checklist.items[2].id == 3
        assert checklist.items[2].text == "Task 3"
        assert checklist.modified_by_agent is False

    def test_empty_list(self):
        """Test creating checklist from empty list."""
        checklist = initialize_checklist([])
        assert len(checklist.items) == 0
