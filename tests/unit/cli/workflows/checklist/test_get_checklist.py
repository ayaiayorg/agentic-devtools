"""Tests for GetChecklist."""

from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows.checklist import (
    get_checklist,
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
