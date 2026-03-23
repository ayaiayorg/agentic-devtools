"""Tests for agentic_devtools.state.set_value."""

from unittest.mock import patch

from agentic_devtools import state


class TestSetValue:
    """Tests for set_value function."""

    def test_set_and_get_value(self, temp_state_dir):
        """Test setting and getting a simple value."""
        state.set_value("test_key", "test_value")
        assert state.get_value("test_key") == "test_value"

    def test_set_integer_value(self, temp_state_dir):
        """Test setting an integer value."""
        state.set_value("count", 42)
        assert state.get_value("count") == 42

    def test_set_float_value(self, temp_state_dir):
        """Test setting a float value."""
        state.set_value("ratio", 3.14)
        assert state.get_value("ratio") == 3.14

    def test_set_boolean_value(self, temp_state_dir):
        """Test setting a boolean value."""
        state.set_value("flag", True)
        assert state.get_value("flag") is True

    def test_set_list_value(self, temp_state_dir):
        """Test setting a list value."""
        items = ["a", "b", "c"]
        state.set_value("items", items)
        assert state.get_value("items") == items

    def test_set_dict_value(self, temp_state_dir):
        """Test setting a dictionary value."""
        config = {"key": "value", "nested": {"inner": 1}}
        state.set_value("config", config)
        assert state.get_value("config") == config

    def test_set_value_calls_mark_dirty(self, temp_state_dir):
        """set_value should call mark_dirty after writing state."""
        with patch("agentic_devtools.cli.git.agdt_branch.mark_dirty") as mock_mark:
            state.set_value("foo", "bar")

        mock_mark.assert_called_once()

    def test_set_value_tolerates_import_error(self, temp_state_dir):
        """set_value does not fail when agdt_branch is not importable."""
        # Temporarily make the module unimportable so the lazy import
        # inside set_value() raises ImportError at import time.
        import sys

        saved = sys.modules.pop("agentic_devtools.cli.git.agdt_branch", None)
        try:
            with patch.dict(sys.modules, {"agentic_devtools.cli.git.agdt_branch": None}):
                # Should not raise despite the module being unimportable
                state.set_value("foo", "bar")
        finally:
            if saved is not None:
                sys.modules["agentic_devtools.cli.git.agdt_branch"] = saved

        assert state.get_value("foo") == "bar"


class TestSetValueSpecialCharacters:
    """Tests for handling special characters in set_value."""

    def test_parentheses_in_content(self, temp_state_dir):
        """Test that parentheses are preserved."""
        content = "This (has) parentheses"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_brackets_in_content(self, temp_state_dir):
        """Test that brackets are preserved."""
        content = "Array [0] and [1]"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_braces_in_content(self, temp_state_dir):
        """Test that braces are preserved."""
        content = "Object {key: value}"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_mixed_special_characters(self, temp_state_dir):
        """Test mixed special characters."""
        content = "func(arg) { return array[0]; }"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_unicode_characters(self, temp_state_dir):
        """Test Unicode characters are preserved."""
        content = "Größe Übung Äpfel 你好 🎉"
        state.set_value("content", content)
        assert state.get_value("content") == content


class TestSetValueMultilineContent:
    """Tests for handling multiline content in set_value."""

    def test_simple_multiline(self, temp_state_dir):
        """Test simple multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_multiline_with_empty_lines(self, temp_state_dir):
        """Test multiline with empty lines."""
        content = "Line 1\n\nLine 3 after empty"
        state.set_value("content", content)
        assert state.get_value("content") == content

    def test_multiline_with_special_chars(self, temp_state_dir):
        """Test multiline with special characters."""
        content = """Thanks for the feedback!

I've fixed the issue:
- Updated function(arg)
- Fixed array[0] access
- Changed {config}"""
        state.set_value("content", content)
        assert state.get_value("content") == content


class TestSetValueBootstrapWiring:
    """Tests for bootstrap worktree_key sync inside set_value."""

    def test_jira_issue_key_updates_bootstrap(self, tmp_path, monkeypatch):
        """set_value('jira.issue_key', ...) updates bootstrap worktree_key."""
        import json

        # Create a bootstrap file so the updater can find it
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "ama"}), encoding="utf-8")

        # The state dir is under .agdt/workflows/... so the CWD walk-up finds .agdt
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        with patch.object(state, "get_state_dir", return_value=state_dir):
            state.set_value("jira.issue_key", "PROJECT-1234")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "PROJECT-1234"
        assert data["identity"] == "ama"

    def test_pull_request_id_updates_bootstrap(self, tmp_path, monkeypatch):
        """set_value('pull_request_id', ...) updates bootstrap with PR prefix."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "xyz"}), encoding="utf-8")

        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        with patch.object(state, "get_state_dir", return_value=state_dir):
            state.set_value("pull_request_id", 42)

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "PR42"

    def test_empty_value_skips_bootstrap(self, tmp_path, monkeypatch):
        """set_value with empty string skips bootstrap update."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "ama"}), encoding="utf-8")

        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        with patch.object(state, "get_state_dir", return_value=state_dir):
            state.set_value("jira.issue_key", "  ")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        # No worktree_key should be added
        assert "worktree_key" not in data

    def test_non_context_key_skips_bootstrap(self, temp_state_dir):
        """set_value for non-context keys does not touch bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("some_other_key", "value")

        mock_update.assert_not_called()

    def test_bootstrap_failure_does_not_break_set_value(self, temp_state_dir):
        """Bootstrap write failure is non-fatal."""
        with patch.object(state, "_update_bootstrap_worktree_key", side_effect=RuntimeError("fail")):
            # Should not raise
            state.set_value("jira.issue_key", "PROJ-1")

        assert state.get_value("jira.issue_key") == "PROJ-1"

    def test_non_string_jira_key_skips_bootstrap(self, temp_state_dir):
        """set_value('jira.issue_key', non-str) does not touch bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("jira.issue_key", 123)

        mock_update.assert_not_called()

    def test_non_digit_pr_id_skips_bootstrap(self, temp_state_dir):
        """set_value('pull_request_id', 'abc') does not touch bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("pull_request_id", "abc")

        mock_update.assert_not_called()

    def test_dict_value_for_jira_key_skips_bootstrap(self, temp_state_dir):
        """set_value('jira.issue_key', dict) does not touch bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("jira.issue_key", {"bad": "input"})

        mock_update.assert_not_called()

    def test_string_digit_pr_id_updates_bootstrap(self, tmp_path, monkeypatch):
        """set_value('pull_request_id', '42') updates bootstrap with PR prefix."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "xyz"}), encoding="utf-8")

        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        with patch.object(state, "get_state_dir", return_value=state_dir):
            state.set_value("pull_request_id", "42")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "PR42"

    def test_bool_pr_id_skips_bootstrap(self, temp_state_dir):
        """set_value('pull_request_id', True) must not write PRTrue/PR1."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("pull_request_id", True)

        mock_update.assert_not_called()

    def test_none_jira_key_skips_bootstrap(self, temp_state_dir):
        """set_value('jira.issue_key', None) does not touch bootstrap."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("jira.issue_key", None)

        mock_update.assert_not_called()


class TestSetValueBootstrapPriorityAware:
    """Tests for priority-aware bootstrap sync in set_value().

    When jira.issue_key is already present in state, set_value("pull_request_id", ...)
    must NOT overwrite the bootstrap worktree_key because the issue key has higher
    priority (matching resolve_worktree_key() in agdt_branch.py).
    """

    def test_set_pull_request_id_skips_bootstrap_when_issue_key_exists(self, temp_state_dir):
        """set_value('pull_request_id', ...) skips bootstrap update when jira.issue_key exists."""
        # Pre-set the issue key in state — it has higher priority
        state.set_value("jira.issue_key", "PROJECT-2779")

        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("pull_request_id", 25858)

        mock_update.assert_not_called()

    def test_set_pull_request_id_updates_bootstrap_when_no_issue_key(self, temp_state_dir):
        """set_value('pull_request_id', ...) updates bootstrap when no jira.issue_key exists."""
        # Ensure no issue key in state
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("pull_request_id", 42)

        mock_update.assert_called_once_with("PR42")

    def test_set_pull_request_id_skips_bootstrap_when_issue_key_is_string(self, temp_state_dir):
        """set_value('pull_request_id', ...) skips bootstrap for string PR ID when issue key set."""
        state.set_value("jira.issue_key", "PROJ-100")

        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("pull_request_id", "999")

        mock_update.assert_not_called()

    def test_set_jira_issue_key_still_updates_bootstrap_regardless(self, temp_state_dir):
        """set_value('jira.issue_key', ...) always updates bootstrap — it is the priority key."""
        # Even if pull_request_id is already set, jira.issue_key must update bootstrap
        state.set_value("pull_request_id", "12345")  # may or may not update bootstrap

        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("jira.issue_key", "PROJECT-5678")

        mock_update.assert_called_once_with("PROJECT-5678")

    def test_set_pull_request_id_still_updates_bootstrap_when_state_empty_despite_scoped_bootstrap(
        self, temp_state_dir
    ):
        """Documents a known limitation: the engine-side guard only checks the state dict.

        When bootstrap is already scoped to an issue key (via _ensure_bootstrap_identity_and_scope),
        but jira.issue_key has NOT yet been written to state (e.g., state was just cleared),
        set_value("pull_request_id", ...) WILL still update the bootstrap to PR<id> because the
        state dict is empty and the guard finds no issue key.

        This is why workflow initiation commands MUST:
        1. Call _ensure_bootstrap_identity_and_scope() BEFORE clear_state_for_workflow_initiation()
        2. Write jira.issue_key to state BEFORE pull_request_id when both are provided

        The caller-side ordering fix is therefore essential and cannot be replaced by
        the engine-side guard alone.
        """
        # State is empty (simulating just-cleared state after clear_state_for_workflow_initiation)
        # The bootstrap is scoped to PROJECT-2779, but state.json has no jira.issue_key yet
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            state.set_value("pull_request_id", 25858)  # state is empty — guard sees no issue key

        # The bootstrap IS overwritten because the guard only checks state dict, not bootstrap file
        mock_update.assert_called_once_with("PR25858")


class TestSetValueBootstrapPriorityAwareNonDictJira:
    """Tests for defensive handling of non-dict state['jira'] in the priority guard.

    If state['jira'] exists but is not a dict (e.g., corrupted/stale state where someone
    set 'jira' to a string), the guard must treat it as "no issue key present" and allow
    the bootstrap update for pull_request_id to proceed.
    """

    def test_set_pull_request_id_updates_bootstrap_when_jira_is_string(self, temp_state_dir):
        """set_value('pull_request_id', ...) updates bootstrap when state['jira'] is a non-dict.

        If state['jira'] is a string (corrupted state), the guard must not raise and
        must not silently suppress the bootstrap update — it should treat it as "no
        issue key" and allow the PR-based update to proceed.
        """
        # Force jira to be a non-dict value (simulates corrupted state)
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            # Manually inject a non-dict 'jira' into the state dict via load/save
            # We bypass set_value to avoid the normal nesting behaviour
            current = state.load_state()
            current["jira"] = "corrupted-string"
            state.save_state(current)

            state.set_value("pull_request_id", 99)

        # Bootstrap must be updated — non-dict jira does not block the update
        mock_update.assert_called_once_with("PR99")

    def test_set_pull_request_id_updates_bootstrap_when_jira_is_list(self, temp_state_dir):
        """set_value('pull_request_id', ...) updates bootstrap when state['jira'] is a list."""
        with patch.object(state, "_update_bootstrap_worktree_key") as mock_update:
            current = state.load_state()
            current["jira"] = ["some", "list"]
            state.save_state(current)

            state.set_value("pull_request_id", 100)

        mock_update.assert_called_once_with("PR100")
