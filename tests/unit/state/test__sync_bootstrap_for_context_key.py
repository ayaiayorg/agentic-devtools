"""Tests for agentic_devtools.state._sync_bootstrap_for_context_key."""

from unittest.mock import patch

from agentic_devtools import state


class TestSyncBootstrapForContextKey:
    """Tests for _sync_bootstrap_for_context_key helper."""

    def test_issue_key_string_updates_bootstrap(self, temp_state_dir):
        """issue_key string value updates bootstrap worktree_key."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", "42", {})

        mock_update.assert_called_once_with("42")

    def test_issue_key_int_updates_bootstrap(self, temp_state_dir):
        """issue_key int value updates bootstrap worktree_key (JSON-parsed)."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", 42, {})

        mock_update.assert_called_once_with("42")

    def test_issue_key_empty_string_skips_bootstrap(self, temp_state_dir):
        """issue_key empty string does not update bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", "", {})

        mock_update.assert_not_called()

    def test_issue_key_bool_skips_bootstrap(self, temp_state_dir):
        """issue_key bool does not update bootstrap (bool is int subclass)."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", True, {})

        mock_update.assert_not_called()

    def test_issue_key_dict_skips_bootstrap(self, temp_state_dir):
        """issue_key dict does not update bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("issue_key", {"bad": "input"}, {})

        mock_update.assert_not_called()

    def test_jira_issue_key_string_updates_bootstrap(self, temp_state_dir):
        """jira.issue_key string value updates bootstrap worktree_key."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("jira.issue_key", "PROJECT-1234", {})

        mock_update.assert_called_once_with("PROJECT-1234")

    def test_jira_issue_key_non_string_skips_bootstrap(self, temp_state_dir):
        """jira.issue_key non-string does not update bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("jira.issue_key", 123, {})

        mock_update.assert_not_called()

    def test_pull_request_id_int_updates_bootstrap(self, temp_state_dir):
        """pull_request_id int updates bootstrap with PR prefix."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {})

        mock_update.assert_called_once_with("PR42")

    def test_pull_request_id_skips_when_issue_key_set(self, temp_state_dir):
        """pull_request_id skips bootstrap when issue_key already in state."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"issue_key": "99"})

        mock_update.assert_not_called()

    def test_pull_request_id_skips_when_int_issue_key_set(self, temp_state_dir):
        """pull_request_id skips bootstrap when issue_key is an int in state."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("pull_request_id", 42, {"issue_key": 99})

        mock_update.assert_not_called()

    def test_non_context_key_is_noop(self, temp_state_dir):
        """Non-context key does not trigger bootstrap update."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state._sync_bootstrap_for_context_key("some_key", "value", {})

        mock_update.assert_not_called()

    def test_exception_is_swallowed(self, temp_state_dir):
        """Bootstrap failure is non-fatal — exception is swallowed."""
        with patch.object(state, "_update_bootstrap_worktree_key", side_effect=RuntimeError("fail")):
            # Should not raise
            state._sync_bootstrap_for_context_key("issue_key", "42", {})
