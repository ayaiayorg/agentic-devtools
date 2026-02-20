"""Tests for Checklist."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import (
    Checklist,
    ChecklistItem,
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


class TestChecklist:
    """Tests for Checklist dataclass."""

    def test_create_empty_checklist(self):
        """Test creating an empty checklist."""
        checklist = Checklist()
        assert checklist.items == []
        assert checklist.modified_by_agent is False

    def test_create_with_items(self):
        """Test creating checklist with items."""
        items = [
            ChecklistItem(id=1, text="Task 1"),
            ChecklistItem(id=2, text="Task 2"),
        ]
        checklist = Checklist(items=items)
        assert len(checklist.items) == 2

    def test_to_dict(self):
        """Test serialization to dict."""
        items = [ChecklistItem(id=1, text="Task")]
        checklist = Checklist(items=items, modified_by_agent=True)
        result = checklist.to_dict()
        assert result == {
            "items": [{"id": 1, "text": "Task", "completed": False}],
            "modified_by_agent": True,
        }

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "items": [{"id": 1, "text": "Task", "completed": True}],
            "modified_by_agent": False,
        }
        checklist = Checklist.from_dict(data)
        assert len(checklist.items) == 1
        assert checklist.items[0].completed is True

    def test_get_item_exists(self):
        """Test getting an existing item."""
        items = [ChecklistItem(id=1, text="Task")]
        checklist = Checklist(items=items)
        item = checklist.get_item(1)
        assert item is not None
        assert item.text == "Task"

    def test_get_item_not_exists(self):
        """Test getting a non-existent item."""
        checklist = Checklist()
        item = checklist.get_item(999)
        assert item is None

    def test_mark_completed(self):
        """Test marking items as complete."""
        items = [
            ChecklistItem(id=1, text="Task 1"),
            ChecklistItem(id=2, text="Task 2"),
        ]
        checklist = Checklist(items=items)
        marked = checklist.mark_completed([1, 2])
        assert marked == [1, 2]
        assert checklist.items[0].completed is True
        assert checklist.items[1].completed is True

    def test_mark_completed_already_complete(self):
        """Test marking already complete items returns empty."""
        items = [ChecklistItem(id=1, text="Task", completed=True)]
        checklist = Checklist(items=items)
        marked = checklist.mark_completed([1])
        assert marked == []

    def test_mark_completed_nonexistent_item(self):
        """Test marking non-existent item is ignored."""
        checklist = Checklist()
        marked = checklist.mark_completed([999])
        assert marked == []

    def test_all_complete_true(self):
        """Test all_complete returns True when all done."""
        items = [
            ChecklistItem(id=1, text="Task 1", completed=True),
            ChecklistItem(id=2, text="Task 2", completed=True),
        ]
        checklist = Checklist(items=items)
        assert checklist.all_complete() is True

    def test_all_complete_false(self):
        """Test all_complete returns False when not all done."""
        items = [
            ChecklistItem(id=1, text="Task 1", completed=True),
            ChecklistItem(id=2, text="Task 2", completed=False),
        ]
        checklist = Checklist(items=items)
        assert checklist.all_complete() is False

    def test_all_complete_empty(self):
        """Test all_complete returns False for empty checklist."""
        checklist = Checklist()
        assert checklist.all_complete() is False

    def test_completion_status(self):
        """Test completion_status returns counts."""
        items = [
            ChecklistItem(id=1, text="Task 1", completed=True),
            ChecklistItem(id=2, text="Task 2", completed=False),
            ChecklistItem(id=3, text="Task 3", completed=True),
        ]
        checklist = Checklist(items=items)
        completed, total = checklist.completion_status()
        assert completed == 2
        assert total == 3

    def test_add_item(self):
        """Test adding a new item."""
        checklist = Checklist()
        item = checklist.add_item("New task")
        assert item.id == 1
        assert item.text == "New task"
        assert len(checklist.items) == 1
        assert checklist.modified_by_agent is True

    def test_add_item_increments_id(self):
        """Test adding items increments ID."""
        items = [ChecklistItem(id=5, text="Existing")]
        checklist = Checklist(items=items)
        item = checklist.add_item("New")
        assert item.id == 6

    def test_remove_item(self):
        """Test removing an item."""
        items = [ChecklistItem(id=1, text="Task")]
        checklist = Checklist(items=items)
        result = checklist.remove_item(1)
        assert result is True
        assert len(checklist.items) == 0
        assert checklist.modified_by_agent is True

    def test_remove_item_not_exists(self):
        """Test removing non-existent item returns False."""
        checklist = Checklist()
        result = checklist.remove_item(999)
        assert result is False

    def test_update_item(self):
        """Test updating an item's text."""
        items = [ChecklistItem(id=1, text="Old text")]
        checklist = Checklist(items=items)
        result = checklist.update_item(1, "New text")
        assert result is True
        assert checklist.items[0].text == "New text"
        assert checklist.modified_by_agent is True

    def test_update_item_not_exists(self):
        """Test updating non-existent item returns False."""
        checklist = Checklist()
        result = checklist.update_item(999, "Text")
        assert result is False

    def test_render_markdown_incomplete(self):
        """Test markdown rendering with incomplete items."""
        items = [
            ChecklistItem(id=1, text="Task 1", completed=False),
            ChecklistItem(id=2, text="Task 2", completed=True),
        ]
        checklist = Checklist(items=items)
        result = checklist.render_markdown()
        assert "⬜ 1. Task 1" in result
        assert "✅ 2. Task 2" in result

    def test_render_plain(self):
        """Test plain text rendering."""
        items = [
            ChecklistItem(id=1, text="Task 1", completed=False),
            ChecklistItem(id=2, text="Task 2", completed=True),
        ]
        checklist = Checklist(items=items)
        result = checklist.render_plain()
        assert "[ ] 1. Task 1" in result
        assert "[x] 2. Task 2" in result
