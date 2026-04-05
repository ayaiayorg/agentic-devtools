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
            context={"jira_issue_key": "PROJECT-5678"},
        )
        result = commands._get_issue_key_from_state()
        assert result == "PROJECT-5678"

    def test_returns_none_when_workflow_has_no_context(self, temp_state_dir, clear_state_before):
        """Test returns None when workflow has no context."""
        state.set_value("workflow", {"name": "test", "status": "in-progress"})
        result = commands._get_issue_key_from_state()
        assert result is None

    def test_returns_top_level_issue_key(self, temp_state_dir, clear_state_before):
        """Test returns top-level issue_key when set."""
        state.set_value("issue_key", "42")
        result = commands._get_issue_key_from_state()
        assert result == "42"

    def test_issue_key_takes_priority_over_jira_issue_key(self, temp_state_dir, clear_state_before):
        """Test issue_key takes priority over jira.issue_key."""
        state.set_value("issue_key", "#42")
        state.set_value("jira.issue_key", "PROJECT-1234")
        result = commands._get_issue_key_from_state()
        assert result == "#42"

    def test_falls_back_to_jira_issue_key(self, temp_state_dir, clear_state_before):
        """Test falls back to jira.issue_key when issue_key is not set."""
        state.set_value("jira.issue_key", "PROJECT-1234")
        result = commands._get_issue_key_from_state()
        assert result == "PROJECT-1234"

    def test_github_issue_number_as_issue_key(self, temp_state_dir, clear_state_before):
        """Test GitHub-format issue numbers work as issue_key values."""
        state.set_value("issue_key", "#42")
        result = commands._get_issue_key_from_state()
        assert result == "#42"

    def test_numeric_issue_key(self, temp_state_dir, clear_state_before):
        """Test numeric issue key (GitHub issue number without #)."""
        state.set_value("issue_key", "42")
        result = commands._get_issue_key_from_state()
        assert result == "42"
