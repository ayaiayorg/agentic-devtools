"""Tests for checklist-related workflow commands."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.cli.workflows.manager import NotifyEventResult, WorkflowEvent, notify_workflow_event


@pytest.fixture
def temp_state_dir(tmp_path):
    """Use a temporary directory for state storage."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state_file = temp_state_dir / "dfly-state.json"
    if state_file.exists():
        state_file.unlink()
    yield


class TestChecklistCreatedEvent:
    """Tests for CHECKLIST_CREATED workflow event."""

    def test_advances_from_checklist_creation_to_implementation(self, temp_state_dir, clear_state_before, capsys):
        """Test that CHECKLIST_CREATED event immediately advances to implementation."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)

        assert isinstance(result, NotifyEventResult)
        assert result.triggered is True
        # Since CHECKLIST_CREATED has auto_advance=True (default) and no required_tasks,
        # it should immediately advance and render the prompt
        assert result.immediate_advance is True
        assert result.prompt_rendered is True
        assert result.new_step == "implementation"
        workflow = state.get_workflow_state()
        # State should be updated directly (not pending_transition)
        assert workflow["step"] == "implementation"
        # Verify the prompt was printed
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "implementation" in captured.out

    def test_no_effect_on_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that CHECKLIST_CREATED does nothing when not in checklist-creation step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="planning",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_CREATED)

        assert result.triggered is False
        workflow = state.get_workflow_state()
        assert "pending_transition" not in workflow.get("context", {})


class TestChecklistCompleteEvent:
    """Tests for CHECKLIST_COMPLETE workflow event."""

    def test_advances_from_implementation_to_review(self, temp_state_dir, clear_state_before, capsys):
        """Test that CHECKLIST_COMPLETE event immediately advances to implementation-review."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)

        assert isinstance(result, NotifyEventResult)
        assert result.triggered is True
        # Since CHECKLIST_COMPLETE has auto_advance=True and no required_tasks,
        # it should immediately advance and render the prompt
        assert result.immediate_advance is True
        assert result.prompt_rendered is True
        assert result.new_step == "implementation-review"
        workflow = state.get_workflow_state()
        # State should be updated directly (not pending_transition)
        assert workflow["step"] == "implementation-review"
        # Verify the prompt was printed
        captured = capsys.readouterr()
        assert "WORKFLOW ADVANCED" in captured.out
        assert "implementation-review" in captured.out

    def test_no_effect_on_wrong_step(self, temp_state_dir, clear_state_before):
        """Test that CHECKLIST_COMPLETE does nothing when not in implementation step."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="verification",
            context={"jira_issue_key": "DFLY-1850"},
        )

        result = notify_workflow_event(WorkflowEvent.CHECKLIST_COMPLETE)

        assert result.triggered is False


class TestCreateChecklistCmd:
    """Tests for dfly-create-checklist command."""

    def test_requires_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires work-on-jira-issue workflow."""
        # No workflow active
        with patch.object(sys, "argv", ["dfly-create-checklist", "Task 1|Task 2"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.create_checklist_cmd()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "requires an active work-on-jira-issue workflow" in captured.err

    def test_requires_items(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires checklist items."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        with patch.object(sys, "argv", ["dfly-create-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.create_checklist_cmd()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "No checklist items provided" in captured.err

    def test_creates_checklist_from_args(self, temp_state_dir, clear_state_before, capsys):
        """Test creating checklist from CLI arguments."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        with patch.object(sys, "argv", ["dfly-create-checklist", "Task 1|Task 2|Task 3"]):
            commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "CHECKLIST CREATED" in captured.out
        assert "3 items:" in captured.out

    def test_creates_checklist_from_state(self, temp_state_dir, clear_state_before, capsys):
        """Test creating checklist from state key."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )
        state.set_value("checklist_items", "First task\nSecond task")

        with patch.object(sys, "argv", ["dfly-create-checklist"]):
            commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "CHECKLIST CREATED" in captured.out
        assert "2 items:" in captured.out

    def test_strips_leading_numbers(self, temp_state_dir, clear_state_before, capsys):
        """Test that leading numbers are stripped from items."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1850"},
        )

        with patch.object(sys, "argv", ["dfly-create-checklist", "1. Task one|2. Task two"]):
            commands.create_checklist_cmd()

        # Verify the checklist was saved without leading numbers
        from agentic_devtools.cli.workflows.checklist import get_checklist

        checklist = get_checklist()
        assert checklist is not None
        assert checklist.items[0].text == "Task one"
        assert checklist.items[1].text == "Task two"


class TestUpdateChecklistCmd:
    """Tests for dfly-update-checklist command."""

    def test_requires_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires work-on-jira-issue workflow."""
        with patch.object(sys, "argv", ["dfly-update-checklist", "--complete", "1"]):
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

        with patch.object(sys, "argv", ["dfly-update-checklist", "--complete", "1"]):
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

        with patch.object(sys, "argv", ["dfly-update-checklist"]):
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

        with patch.object(sys, "argv", ["dfly-update-checklist", "--complete", "1,2"]):
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

        with patch.object(sys, "argv", ["dfly-update-checklist", "--add", "New task"]):
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

        with patch.object(sys, "argv", ["dfly-update-checklist", "--complete", "1"]):
            commands.update_checklist_cmd()

        captured = capsys.readouterr()
        assert "All items complete!" in captured.out
        assert "implementation-review" in captured.out


class TestShowChecklistCmd:
    """Tests for dfly-show-checklist command."""

    def test_requires_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires work-on-jira-issue workflow."""
        with patch.object(sys, "argv", ["dfly-show-checklist"]):
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

        with patch.object(sys, "argv", ["dfly-show-checklist"]):
            commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "No checklist exists" in captured.out
        assert "dfly-create-checklist" in captured.out

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

        with patch.object(sys, "argv", ["dfly-show-checklist"]):
            commands.show_checklist_cmd()

        captured = capsys.readouterr()
        assert "IMPLEMENTATION CHECKLIST" in captured.out
        assert "(1/2 complete)" in captured.out
        assert "✅ 1. Task 1" in captured.out
        assert "⬜ 2. Task 2" in captured.out
        assert "1 item(s) remaining" in captured.out
