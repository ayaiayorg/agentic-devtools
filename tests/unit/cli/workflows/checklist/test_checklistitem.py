"""Tests for ChecklistItem."""

import pytest

from agentic_devtools.cli.workflows.checklist import (
    ChecklistItem,
)


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "agdt-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestChecklistItem:
    """Tests for ChecklistItem dataclass."""

    def test_create_item(self):
        """Test creating a checklist item."""
        item = ChecklistItem(id=1, text="Test task")
        assert item.id == 1
        assert item.text == "Test task"
        assert item.completed is False

    def test_create_completed_item(self):
        """Test creating a completed item."""
        item = ChecklistItem(id=2, text="Done task", completed=True)
        assert item.completed is True

    def test_to_dict(self):
        """Test serialization to dict."""
        item = ChecklistItem(id=1, text="Test", completed=True)
        result = item.to_dict()
        assert result == {"id": 1, "text": "Test", "completed": True}

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {"id": 3, "text": "From dict", "completed": False}
        item = ChecklistItem.from_dict(data)
        assert item.id == 3
        assert item.text == "From dict"
        assert item.completed is False

    def test_from_dict_default_completed(self):
        """Test deserialization defaults completed to False."""
        data = {"id": 1, "text": "No completed key"}
        item = ChecklistItem.from_dict(data)
        assert item.completed is False
