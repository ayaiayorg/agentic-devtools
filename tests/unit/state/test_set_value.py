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

    def test_jira_issue_key_updates_bootstrap(self, tmp_path):
        """set_value('jira.issue_key', ...) updates bootstrap worktree_key."""
        import json

        # Create a bootstrap file so the updater can find it
        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "ama"}), encoding="utf-8")

        # The state dir is under .agdt/workflows/... so the walk-up finds .agdt
        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        with patch.object(state, "get_state_dir", return_value=state_dir):
            state.set_value("jira.issue_key", "DFLY-1234")

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "DFLY-1234"
        assert data["identity"] == "ama"

    def test_pull_request_id_updates_bootstrap(self, tmp_path):
        """set_value('pull_request_id', ...) updates bootstrap with PR prefix."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "xyz"}), encoding="utf-8")

        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

        with patch.object(state, "get_state_dir", return_value=state_dir):
            state.set_value("pull_request_id", 42)

        data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
        assert data["worktree_key"] == "PR42"

    def test_empty_value_skips_bootstrap(self, tmp_path):
        """set_value with empty string skips bootstrap update."""
        import json

        agdt_dir = tmp_path / ".agdt"
        agdt_dir.mkdir(parents=True)
        bootstrap_path = agdt_dir / "runtime-bootstrap.json"
        bootstrap_path.write_text(json.dumps({"identity": "ama"}), encoding="utf-8")

        state_dir = tmp_path / ".agdt" / "workflows" / "_unscoped"
        state_dir.mkdir(parents=True)

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
