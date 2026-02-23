"""Tests for ShowChecklistCmd."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


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


@pytest.fixture
def mock_workflow_state_clearing():
    """Mock clear_state_for_workflow_initiation to be a no-op.

    This is needed because workflow initiation commands clear all state at the start,
    but tests set up state before calling the command. Without this mock, the test's
    state setup would be wiped immediately.
    """
    with patch("agentic_devtools.cli.workflows.commands.clear_state_for_workflow_initiation"):
        yield


class TestShowChecklistCmd:
    """Tests for show_checklist_cmd function."""

    def test_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no workflow is active."""
        with pytest.raises(SystemExit) as exc_info:
            commands.show_checklist_cmd()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No active work-on-jira-issue workflow" in captured.err

    def test_no_checklist_exists(self, temp_state_dir, clear_state_before, capsys):
        """Test message when no checklist exists."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "No checklist exists" in captured.out
        assert "agdt-create-checklist" in captured.out

    def test_show_checklist_with_items(self, temp_state_dir, clear_state_before, capsys):
        """Test showing a checklist with items."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(
            items=[
                ChecklistItem(id=1, text="Task 1", completed=True),
                ChecklistItem(id=2, text="Task 2"),
            ]
        )
        save_checklist(checklist)

        commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "IMPLEMENTATION CHECKLIST (1/2 complete)" in captured.out
        assert "1 item(s) remaining" in captured.out

    def test_show_checklist_all_complete(self, temp_state_dir, clear_state_before, capsys):
        """Test showing a checklist with all items complete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(
            items=[
                ChecklistItem(id=1, text="Task 1", completed=True),
                ChecklistItem(id=2, text="Task 2", completed=True),
            ]
        )
        save_checklist(checklist)

        commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "IMPLEMENTATION CHECKLIST (2/2 complete)" in captured.out
        assert "All items complete" in captured.out


class TestShowChecklistCmdFromChecklistCommands:
    """Tests for dfly-show-checklist command."""

    def test_requires_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires work-on-jira-issue workflow."""
        with patch.object(sys, "argv", ["agdt-show-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.show_checklist_cmd()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No active work-on-jira-issue workflow" in captured.err

    def test_no_checklist_message(self, temp_state_dir, clear_state_before, capsys):
        """Test message when no checklist exists."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        with patch.object(sys, "argv", ["agdt-show-checklist"]):
            commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "No checklist exists" in captured.out
        assert "agdt-create-checklist" in captured.out

    def test_displays_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test displaying existing checklist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1850",
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": True},
                        {"id": 2, "text": "Task 2", "completed": False},
                    ],
                    "modified_by_agent": False,
                },
            },
        )

        with patch.object(sys, "argv", ["agdt-show-checklist"]):
            commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "IMPLEMENTATION CHECKLIST" in captured.out
        assert "(1/2 complete)" in captured.out
        assert "✅ 1. Task 1" in captured.out
        assert "⬜ 2. Task 2" in captured.out
        assert "1 item(s) remaining" in captured.out
