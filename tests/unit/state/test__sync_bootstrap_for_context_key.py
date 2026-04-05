"""Tests for agentic_devtools.state._sync_bootstrap_for_context_key."""

from unittest.mock import patch

from agentic_devtools import state


class TestSyncBootstrapForContextKeyIssueKey:
    """Tests for _sync_bootstrap_for_context_key with issue_key."""

    def test_string_issue_key_updates_bootstrap(self, temp_state_dir):
        """String issue_key triggers bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", "PROJECT-42", {})

        mock_update.assert_called_once_with("PROJECT-42")

    def test_int_issue_key_updates_bootstrap(self, temp_state_dir):
        """Int issue_key triggers bootstrap update with stringified value."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", 42, {})

        mock_update.assert_called_once_with("42")

    def test_empty_string_skips_bootstrap(self, temp_state_dir):
        """Empty string does not trigger bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", "", {})

        mock_update.assert_not_called()

    def test_whitespace_string_skips_bootstrap(self, temp_state_dir):
        """Whitespace-only string does not trigger bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", "  ", {})

        mock_update.assert_not_called()

    def test_bool_issue_key_skips_bootstrap(self, temp_state_dir):
        """Bool values are rejected (bool is int subclass)."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", True, {})

        mock_update.assert_not_called()

    def test_dict_issue_key_skips_bootstrap(self, temp_state_dir):
        """Dict values are rejected."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", {"bad": "input"}, {})

        mock_update.assert_not_called()

    def test_list_issue_key_skips_bootstrap(self, temp_state_dir):
        """List values are rejected."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", ["bad"], {})

        mock_update.assert_not_called()


class TestSyncBootstrapForContextKeyJiraIssueKey:
    """Tests for _sync_bootstrap_for_context_key with jira.issue_key."""

    def test_string_jira_key_updates_bootstrap(self, temp_state_dir):
        """String jira.issue_key triggers bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("jira.issue_key", "PROJECT-1234", {})

        mock_update.assert_called_once_with("PROJECT-1234")

    def test_empty_string_skips_bootstrap(self, temp_state_dir):
        """Empty jira.issue_key does not trigger bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("jira.issue_key", "", {})

        mock_update.assert_not_called()

    def test_non_string_skips_bootstrap(self, temp_state_dir):
        """Non-string jira.issue_key does not trigger bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("jira.issue_key", 123, {})

        mock_update.assert_not_called()


class TestSyncBootstrapForContextKeyPullRequestId:
    """Tests for _sync_bootstrap_for_context_key with pull_request_id."""

    def test_int_pr_id_updates_bootstrap(self, temp_state_dir):
        """Int pull_request_id triggers bootstrap update with PR prefix."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {})

        mock_update.assert_called_once_with("PR42")

    def test_digit_string_pr_id_updates_bootstrap(self, temp_state_dir):
        """Digit string pull_request_id triggers bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", "42", {})

        mock_update.assert_called_once_with("PR42")

    def test_non_digit_string_skips_bootstrap(self, temp_state_dir):
        """Non-digit string pull_request_id does not trigger bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", "abc", {})

        mock_update.assert_not_called()

    def test_bool_pr_id_skips_bootstrap(self, temp_state_dir):
        """Bool pull_request_id does not trigger bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", True, {})

        mock_update.assert_not_called()

    def test_skips_when_issue_key_exists(self, temp_state_dir):
        """pull_request_id skips bootstrap when issue_key exists in state."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"issue_key": "PROJECT-1"})

        mock_update.assert_not_called()

    def test_skips_when_int_issue_key_exists(self, temp_state_dir):
        """pull_request_id skips bootstrap when int issue_key exists in state."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"issue_key": 99})

        mock_update.assert_not_called()

    def test_skips_when_jira_issue_key_exists(self, temp_state_dir):
        """pull_request_id skips bootstrap when jira.issue_key exists in state."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"jira": {"issue_key": "PROJ-1"}})

        mock_update.assert_not_called()

    def test_updates_when_issue_key_is_empty(self, temp_state_dir):
        """pull_request_id updates bootstrap when issue_key is empty string."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"issue_key": ""})

        mock_update.assert_called_once_with("PR42")

    def test_updates_when_issue_key_is_bool(self, temp_state_dir):
        """pull_request_id updates bootstrap when issue_key is a bool (rejected type)."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"issue_key": True})

        mock_update.assert_called_once_with("PR42")


class TestSyncBootstrapForContextKeyNonContextKey:
    """Tests for _sync_bootstrap_for_context_key with non-context keys."""

    def test_non_context_key_is_noop(self, temp_state_dir):
        """Non-context key does not trigger any bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("some_other_key", "value", {})

        mock_update.assert_not_called()


class TestSyncBootstrapForContextKeyErrorHandling:
    """Tests for error handling in _sync_bootstrap_for_context_key."""

    def test_exception_is_swallowed(self, temp_state_dir):
        """Exceptions from _update_bootstrap_worktree_key are non-fatal."""
        with patch.object(state, "_update_bootstrap_worktree_key", side_effect=RuntimeError("fail")):
            # Should not raise
            state._sync_bootstrap_for_context_key("issue_key", "42", {})
