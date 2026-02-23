"""Tests for UpdateChecklistCmd."""

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


class TestUpdateChecklistCmd:
    """Tests for update_checklist_cmd function."""

    def test_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no workflow is active."""
        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "requires an active work-on-jira-issue workflow" in captured.err

    def test_no_existing_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no checklist exists."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No checklist exists" in captured.err

    def test_no_operation_specified(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no operation is specified."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        # Create a checklist first
        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1"), ChecklistItem(id=2, text="Task 2")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No operation specified" in captured.err

    def test_add_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test successfully adding an item."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--add", "New task"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Added item" in captured.out
        assert "New task" in captured.out

    def test_remove_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test successfully removing an item."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--remove", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Removed item 1" in captured.out

    def test_remove_item_not_found(self, temp_state_dir, clear_state_before, capsys):
        """Test removing an item that doesn't exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--remove", "99"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 99 not found" in captured.out

    def test_complete_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test marking an item as complete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Marked item 1 complete" in captured.out

    def test_revert_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test reverting an item to incomplete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1", completed=True)])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--revert", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Reverted item 1 to incomplete" in captured.out

    def test_revert_already_incomplete(self, temp_state_dir, clear_state_before, capsys):
        """Test reverting an item that's already incomplete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1", completed=False)])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--revert", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 1 already incomplete" in captured.out

    def test_revert_item_not_found(self, temp_state_dir, clear_state_before, capsys):
        """Test reverting an item that doesn't exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--revert", "99"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 99 not found" in captured.out

    def test_edit_item_success(self, temp_state_dir, clear_state_before, capsys):
        """Test editing an item's text."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "1:New task text"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Updated item 1" in captured.out

    def test_edit_item_invalid_format(self, temp_state_dir, clear_state_before, capsys):
        """Test editing with invalid format (missing colon)."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "1-no-colon"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Invalid edit format" in captured.err

    def test_edit_item_invalid_id(self, temp_state_dir, clear_state_before, capsys):
        """Test editing with invalid item ID (not a number)."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "abc:New text"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Invalid item ID" in captured.err

    def test_edit_item_not_found(self, temp_state_dir, clear_state_before, capsys):
        """Test editing an item that doesn't exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Old task")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--edit", "99:New text"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Item 99 not found" in captured.out

    def test_all_complete_triggers_event(self, temp_state_dir, clear_state_before, capsys):
        """Test completing all items triggers CHECKLIST_COMPLETE event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        from agentic_devtools.cli.workflows.checklist import Checklist, ChecklistItem, save_checklist

        checklist = Checklist(items=[ChecklistItem(id=1, text="Task 1")])
        save_checklist(checklist)

        with patch("sys.argv", ["agdt-update-checklist", "--complete", "1"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=True,
                    immediate_advance=False,
                )
                commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "All items complete" in captured.out
        assert "Workflow transition triggered" in captured.out


class TestUpdateChecklistCmdFromChecklistCommands:
    """Tests for dfly-update-checklist command."""

    def test_requires_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires work-on-jira-issue workflow."""
        with patch.object(sys, "argv", ["agdt-update-checklist", "--complete", "1"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "requires an active work-on-jira-issue workflow" in captured.err

    def test_requires_existing_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires existing checklist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        with patch.object(sys, "argv", ["agdt-update-checklist", "--complete", "1"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No checklist exists" in captured.err

    def test_requires_operation(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires an operation."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1850",
                "checklist": {
                    "items": [{"id": 1, "text": "Task", "completed": False}],
                    "modified_by_agent": False,
                },
            },
        )

        with patch.object(sys, "argv", ["agdt-update-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.update_checklist_cmd()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No operation specified" in captured.err

    def test_complete_items(self, temp_state_dir, clear_state_before, capsys):
        """Test marking items complete."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1850",
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": False},
                        {"id": 2, "text": "Task 2", "completed": False},
                    ],
                    "modified_by_agent": False,
                },
            },
        )

        with patch.object(sys, "argv", ["agdt-update-checklist", "--complete", "1,2"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Marked item 1 complete" in captured.out
        assert "Marked item 2 complete" in captured.out

    def test_add_item(self, temp_state_dir, clear_state_before, capsys):
        """Test adding a new item."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1850",
                "checklist": {
                    "items": [{"id": 1, "text": "Task 1", "completed": False}],
                    "modified_by_agent": False,
                },
            },
        )

        with patch.object(sys, "argv", ["agdt-update-checklist", "--add", "New task"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "Added item 2: New task" in captured.out

    def test_triggers_checklist_complete_event(self, temp_state_dir, clear_state_before, capsys):
        """Test that completing all items triggers CHECKLIST_COMPLETE event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "DFLY-1850",
                "checklist": {
                    "items": [{"id": 1, "text": "Task 1", "completed": False}],
                    "modified_by_agent": False,
                },
            },
        )

        with patch.object(sys, "argv", ["agdt-update-checklist", "--complete", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "All items complete!" in captured.out
        assert "implementation-review" in captured.out
