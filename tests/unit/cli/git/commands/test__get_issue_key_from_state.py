"""Tests for agentic_devtools.cli.git.commands._get_issue_key_from_state."""

from agentic_devtools import state
from agentic_devtools.cli.git import commands


class TestGetIssueKeyFromState:
    """Tests for _get_issue_key_from_state function."""

    def test_returns_none_when_no_workflow(self, temp_state_dir, clear_state_before):
        """Test returns None when no workflow is set."""
        result = commands._get_issue_key_from_state()
        assert result is None

    def test_returns_key_from_workflow_context(self, temp_state_dir, clear_state_before):
        """Test returns jira_issue_key from workflow context."""
        state.set_workflow_state(
            name="work-on-jira-issue",
            status="in-progress",
            step="implementation",
            context={"jira_issue_key": "DFLY-5678"},
        )
        result = commands._get_issue_key_from_state()
        assert result == "DFLY-5678"

    def test_returns_none_when_workflow_has_no_context(self, temp_state_dir, clear_state_before):
        """Test returns None when workflow has no context."""
        state.set_value("workflow", {"name": "test", "status": "in-progress"})
        result = commands._get_issue_key_from_state()
        assert result is None
