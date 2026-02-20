"""Tests for agentic_devtools.cli.git.commands._trigger_implementation_review."""

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestTriggerImplementationReview:
    """Tests for _trigger_implementation_review function."""

    def test_triggers_workflow_event(self, temp_state_dir, clear_state_before):
        """Test triggers CHECKLIST_COMPLETE workflow event."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-1234"},
        )

        # Should not raise
        commands._trigger_implementation_review()

    def test_handles_no_workflow(self, temp_state_dir, clear_state_before):
        """Test handles case when no workflow is active."""
        # Should not raise
        commands._trigger_implementation_review()
