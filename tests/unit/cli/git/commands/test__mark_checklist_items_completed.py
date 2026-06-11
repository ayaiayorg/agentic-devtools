"""Tests for agentic_devtools.cli.git.commands._mark_checklist_items_completed."""

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestMarkChecklistItemsCompleted:
    """Tests for _mark_checklist_items_completed function."""

    def test_does_nothing_when_empty_list(self, temp_state_dir, clear_state_before, capsys):
        """Test does nothing when item_ids is empty."""
        commands._mark_checklist_items_completed([])
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_prints_warning_when_no_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test prints warning when no checklist exists."""
        commands._mark_checklist_items_completed([1, 2])
        captured = capsys.readouterr()
        assert "No checklist found" in captured.out

    def test_marks_items_in_checklist(self, temp_state_dir, clear_state_before, capsys):
        """Test marks items as completed in checklist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "PROJECT-1234",
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": False},
                        {"id": 2, "text": "Task 2", "completed": False},
                    ],
                    "modified_by_agent": False,
                },
            },
        )

        commands._mark_checklist_items_completed([1])

        captured = capsys.readouterr()
        assert "Marked checklist items as completed" in captured.out

    def test_skips_print_when_no_items_marked(self, temp_state_dir, clear_state_before, capsys):
        """Test skips marking message when items are already completed."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "PROJECT-1234",
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": True},
                        {"id": 2, "text": "Task 2", "completed": False},
                    ],
                    "modified_by_agent": False,
                },
            },
        )

        # Item 1 is already completed, so marked list will be empty
        commands._mark_checklist_items_completed([1])

        captured = capsys.readouterr()
        assert "Marked checklist items as completed" not in captured.out

    def test_no_items_marked_when_ids_do_not_exist(self, temp_state_dir, clear_state_before, capsys):
        """Test no items are marked when the provided checklist IDs do not exist."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={
                "jira_issue_key": "PROJECT-1234",
                "checklist": {
                    "items": [
                        {"id": 1, "text": "Task 1", "completed": False},
                    ],
                    "modified_by_agent": False,
                },
            },
        )

        commands._mark_checklist_items_completed([99])

        captured = capsys.readouterr()
        assert "Marked checklist items as completed" not in captured.out
