"""Tests for _clear_stale_issue_keys_for_create helper."""

from agentic_devtools import state
from agentic_devtools.cli.workflows.commands import _clear_stale_issue_keys_for_create


class TestClearStaleIssueKeysForCreate:
    """Tests for _clear_stale_issue_keys_for_create function."""

    def test_clears_both_keys(self, temp_state_dir, capsys):
        """Both issue_key and jira.issue_key are deleted when both present."""
        state.set_value("issue_key", "STALE-111")
        state.set_value("jira.issue_key", "STALE-222")

        _clear_stale_issue_keys_for_create()

        assert state.get_value("issue_key") is None
        assert state.get_value("jira.issue_key") is None

    def test_clears_only_issue_key(self, temp_state_dir, capsys):
        """Only issue_key deleted when jira.issue_key absent."""
        state.set_value("issue_key", "STALE-111")

        _clear_stale_issue_keys_for_create()

        assert state.get_value("issue_key") is None
        assert state.get_value("jira.issue_key") is None

    def test_clears_only_jira_issue_key(self, temp_state_dir, capsys):
        """Only jira.issue_key deleted when issue_key absent."""
        state.set_value("jira.issue_key", "STALE-222")

        _clear_stale_issue_keys_for_create()

        assert state.get_value("issue_key") is None
        assert state.get_value("jira.issue_key") is None

    def test_no_keys_no_message(self, temp_state_dir, capsys):
        """No stderr output when neither key exists."""
        _clear_stale_issue_keys_for_create()

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_stderr_message_format(self, temp_state_dir, capsys):
        """Message matches expected emoji-prefixed format."""
        state.set_value("jira.issue_key", "STALE-100")

        _clear_stale_issue_keys_for_create()

        captured = capsys.readouterr()
        assert "Cleared stale issue selection state" in captured.err
        assert "creating fresh issue" in captured.err

    def test_stderr_lists_cleared_keys(self, temp_state_dir, capsys):
        """Message includes the specific key names that were cleared."""
        state.set_value("issue_key", "STALE-111")
        state.set_value("jira.issue_key", "STALE-222")

        _clear_stale_issue_keys_for_create()

        captured = capsys.readouterr()
        assert "issue_key" in captured.err
        assert "jira.issue_key" in captured.err

    def test_preserves_other_state_keys(self, temp_state_dir, capsys):
        """Other state keys like jira.project_key are not affected."""
        state.set_value("jira.project_key", "PROJ")
        state.set_value("jira.issue_key", "STALE-100")
        state.set_value("other_key", "keep_me")

        _clear_stale_issue_keys_for_create()

        assert state.get_value("jira.project_key") == "PROJ"
        assert state.get_value("other_key") == "keep_me"
