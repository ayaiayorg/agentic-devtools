"""Tests for CreateChecklistCmd."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.workflows import commands
from agentic_devtools.prompts import loader


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


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


class TestCreateChecklistCmd:
    """Tests for create_checklist_cmd function."""

    def test_no_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no workflow is active."""
        with patch("sys.argv", ["agdt-create-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.create_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "requires an active work-on-jira-issue workflow" in captured.err

    def test_no_items_provided(self, temp_state_dir, clear_state_before, capsys):
        """Test error when no checklist items are provided."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist"]):
            with pytest.raises(SystemExit) as exc_info:
                commands.create_checklist_cmd()
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "No checklist items provided" in captured.err

    def test_create_checklist_success(self, temp_state_dir, clear_state_before, capsys):
        """Test successful checklist creation with items from argument."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist", "Task 1|Task 2|Task 3"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=False,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "CHECKLIST CREATED" in captured.out
        assert "3 items" in captured.out

    def test_create_checklist_from_state(self, temp_state_dir, clear_state_before, capsys):
        """Test checklist creation with items from state."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )
        state.set_value("checklist_items", "1. First task\n2. Second task")

        with patch("sys.argv", ["agdt-create-checklist"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=False,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "CHECKLIST CREATED" in captured.out
        assert "2 items" in captured.out

    def test_create_checklist_triggers_event(self, temp_state_dir, clear_state_before, capsys):
        """Test checklist creation triggers workflow event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="checklist-creation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist", "Task 1|Task 2"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=True,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "Workflow transition triggered" in captured.out

    def test_create_checklist_wrong_step_warning(self, temp_state_dir, clear_state_before, capsys):
        """Test warning when creating checklist in wrong step (but no existing checklist)."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",  # Not checklist-creation
            context={"jira_issue_key": "DFLY-1234"},
        )

        with patch("sys.argv", ["agdt-create-checklist", "Task 1"]):
            with patch("agentic_devtools.cli.workflows.manager.notify_workflow_event") as mock_event:
                from agentic_devtools.cli.workflows.manager import NotifyEventResult

                mock_event.return_value = NotifyEventResult(
                    triggered=False,
                    immediate_advance=False,
                )
                commands.create_checklist_cmd()

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "not 'checklist-creation'" in captured.err


class TestCreateChecklistCmdFromChecklistCommands:
    """Tests for dfly-create-checklist command."""

    def test_requires_active_workflow(self, temp_state_dir, clear_state_before, capsys):
        """Test that command requires work-on-jira-issue workflow."""
        # No workflow active
        with patch.object(sys, "argv", ["agdt-create-checklist", "Task 1|Task 2"]):
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

        with patch.object(sys, "argv", ["agdt-create-checklist"]):
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

        with patch.object(sys, "argv", ["agdt-create-checklist", "Task 1|Task 2|Task 3"]):
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

        with patch.object(sys, "argv", ["agdt-create-checklist"]):
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

        with patch.object(sys, "argv", ["agdt-create-checklist", "1. Task one|2. Task two"]):
            commands.create_checklist_cmd()

        # Verify the checklist was saved without leading numbers
        from agentic_devtools.cli.workflows.checklist import get_checklist

        checklist = get_checklist()
        assert checklist is not None
        assert checklist.items[0].text == "Task one"
        assert checklist.items[1].text == "Task two"
