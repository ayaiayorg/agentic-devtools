"""
Tests for agentic-devtools CLI state commands.
"""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import state as cli_state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


class TestSetCommand:
    """Tests for dfly-set command."""

    def test_set_simple_value(self, temp_state_dir, clear_state_before):
        """Test setting a simple value."""
        with patch.object(sys, "argv", ["dfly-set", "key", "value"]):
            cli_state.set_cmd()
        assert state.get_value("key") == "value"

    def test_set_integer_via_json(self, temp_state_dir, clear_state_before):
        """Test setting an integer value (parsed as JSON)."""
        with patch.object(sys, "argv", ["dfly-set", "count", "42"]):
            cli_state.set_cmd()
        assert state.get_value("count") == 42

    def test_set_boolean_true(self, temp_state_dir, clear_state_before):
        """Test setting boolean true."""
        with patch.object(sys, "argv", ["dfly-set", "flag", "true"]):
            cli_state.set_cmd()
        assert state.get_value("flag") is True

    def test_set_boolean_false(self, temp_state_dir, clear_state_before):
        """Test setting boolean false."""
        with patch.object(sys, "argv", ["dfly-set", "flag", "false"]):
            cli_state.set_cmd()
        assert state.get_value("flag") is False

    def test_set_string_with_spaces(self, temp_state_dir, clear_state_before):
        """Test setting a string with spaces."""
        with patch.object(sys, "argv", ["dfly-set", "msg", "hello", "world"]):
            cli_state.set_cmd()
        assert state.get_value("msg") == "hello world"

    def test_set_json_object(self, temp_state_dir, clear_state_before):
        """Test setting a JSON object."""
        with patch.object(sys, "argv", ["dfly-set", "config", '{"key": "value"}']):
            cli_state.set_cmd()
        assert state.get_value("config") == {"key": "value"}

    def test_set_special_characters(self, temp_state_dir, clear_state_before):
        """Test setting content with special characters."""
        content = "func(arg) { return [0]; }"
        with patch.object(sys, "argv", ["dfly-set", "content", content]):
            cli_state.set_cmd()
        assert state.get_value("content") == content

    def test_set_multiline_content(self, temp_state_dir, clear_state_before):
        """Test setting multiline content."""
        content = "Line 1\nLine 2\nLine 3"
        with patch.object(sys, "argv", ["dfly-set", "content", content]):
            cli_state.set_cmd()
        assert state.get_value("content") == content

    def test_set_missing_args_exits(self, temp_state_dir, clear_state_before):
        """Test that missing arguments causes exit."""
        with patch.object(sys, "argv", ["dfly-set"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_state.set_cmd()
            assert exc_info.value.code == 1

    def test_set_from_stdin(self, temp_state_dir, clear_state_before):
        """Test setting value from stdin."""
        stdin_content = "content from stdin"
        with patch.object(sys, "argv", ["dfly-set", "content", "-"]):
            with patch.object(sys, "stdin", StringIO(stdin_content)):
                cli_state.set_cmd()
        assert state.get_value("content") == stdin_content


class TestGetCommand:
    """Tests for dfly-get command."""

    def test_get_existing_value(self, temp_state_dir, clear_state_before):
        """Test getting an existing value."""
        state.set_value("test", "value")
        with patch.object(sys, "argv", ["dfly-get", "test"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_state.get_cmd()
                assert mock_stdout.getvalue().strip() == "value"

    def test_get_nonexistent_exits(self, temp_state_dir, clear_state_before):
        """Test getting nonexistent key exits with error."""
        with patch.object(sys, "argv", ["dfly-get", "nonexistent"]):
            with pytest.raises(SystemExit) as exc_info:
                cli_state.get_cmd()
            assert exc_info.value.code == 1

    def test_get_json_value_pretty_printed(self, temp_state_dir, clear_state_before):
        """Test getting a JSON value is pretty printed."""
        state.set_value("config", {"key": "value"})
        with patch.object(sys, "argv", ["dfly-get", "config"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_state.get_cmd()
                output = mock_stdout.getvalue()
                assert '"key"' in output
                assert '"value"' in output


class TestDeleteCommand:
    """Tests for dfly-delete command."""

    def test_delete_existing_key(self, temp_state_dir, clear_state_before):
        """Test deleting an existing key."""
        state.set_value("to_delete", "value")
        with patch.object(sys, "argv", ["dfly-delete", "to_delete"]):
            cli_state.delete_cmd()
        assert state.get_value("to_delete") is None

    def test_delete_nonexistent_key(self, temp_state_dir, clear_state_before):
        """Test deleting a nonexistent key (no error, just message)."""
        with patch.object(sys, "argv", ["dfly-delete", "nonexistent"]):
            # Should not raise, just print message
            cli_state.delete_cmd()


class TestClearCommand:
    """Tests for dfly-clear command."""

    def test_clear_removes_all_state(self, temp_state_dir, clear_state_before):
        """Test that clear removes all state."""
        state.set_value("key1", "value1")
        state.set_value("key2", "value2")
        with patch.object(sys, "argv", ["dfly-clear"]):
            cli_state.clear_cmd()
        assert state.load_state() == {}


class TestShowCommand:
    """Tests for dfly-show command."""

    def test_show_empty_state(self, temp_state_dir, clear_state_before):
        """Test showing empty state."""
        with patch.object(sys, "argv", ["dfly-show"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_state.show_cmd()
                assert "(empty state)" in mock_stdout.getvalue()

    def test_show_state_with_values(self, temp_state_dir, clear_state_before):
        """Test showing state with values."""
        state.set_value("test", "value")
        with patch.object(sys, "argv", ["dfly-show"]):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli_state.show_cmd()
                output = mock_stdout.getvalue()
                assert "test" in output
                assert "value" in output


class TestSetCommandContextSwitching:
    """Tests for context-switching behavior in set_cmd."""

    def test_set_pull_request_id_uses_set_context_value(self, temp_state_dir, clear_state_before, capsys):
        """Test that setting pull_request_id uses set_context_value."""
        with patch.object(state, "_trigger_cross_lookup"):
            with patch.object(sys, "argv", ["dfly-set", "pull_request_id", "12345"]):
                cli_state.set_cmd()

        assert state.get_value("pull_request_id") == 12345

        captured = capsys.readouterr()
        assert "context switched" in captured.out

    def test_set_jira_issue_key_uses_set_context_value(self, temp_state_dir, clear_state_before, capsys):
        """Test that setting jira.issue_key uses set_context_value."""
        with patch.object(state, "_trigger_cross_lookup"):
            with patch.object(sys, "argv", ["dfly-set", "jira.issue_key", "DFLY-1234"]):
                cli_state.set_cmd()

        assert state.get_value("jira.issue_key") == "DFLY-1234"

        captured = capsys.readouterr()
        assert "context switched" in captured.out

    def test_set_same_pull_request_id_no_context_switch(self, temp_state_dir, clear_state_before, capsys):
        """Test that setting same pull_request_id doesn't trigger context switch."""
        state.set_value("pull_request_id", "12345")
        state.set_value("other_key", "should_persist")

        with patch.object(sys, "argv", ["dfly-set", "pull_request_id", "12345"]):
            cli_state.set_cmd()

        # Other state should be preserved
        assert state.get_value("other_key") == "should_persist"

        captured = capsys.readouterr()
        # Should say "Set pull_request_id" without "context switched"
        assert "Set pull_request_id" in captured.out
        assert "context switched" not in captured.out

    def test_set_different_pull_request_id_clears_state(self, temp_state_dir, clear_state_before, capsys):
        """Test that changing pull_request_id clears other state."""
        state.set_value("pull_request_id", "12345")
        state.set_value("other_key", "should_be_cleared")

        with patch.object(state, "_trigger_cross_lookup"):
            with patch.object(sys, "argv", ["dfly-set", "pull_request_id", "99999"]):
                cli_state.set_cmd()

        # New value should be set
        assert state.get_value("pull_request_id") == 99999

        # Other state should be cleared
        assert state.get_value("other_key") is None

    def test_set_non_context_key_uses_set_value(self, temp_state_dir, clear_state_before, capsys):
        """Test that setting non-context keys uses regular set_value."""
        state.set_value("pull_request_id", "12345")
        state.set_value("other_key", "should_persist")

        with patch.object(sys, "argv", ["dfly-set", "some_key", "some_value"]):
            cli_state.set_cmd()

        # New value should be set
        assert state.get_value("some_key") == "some_value"

        # Other state should be preserved (no clearing)
        assert state.get_value("pull_request_id") == "12345"
        assert state.get_value("other_key") == "should_persist"

        captured = capsys.readouterr()
        assert "Set some_key" in captured.out
        assert "context switched" not in captured.out

    def test_set_context_key_triggers_cross_lookup(self, temp_state_dir, clear_state_before):
        """Test that setting context key triggers cross-lookup."""
        with patch.object(state, "_trigger_cross_lookup") as mock_lookup:
            with patch.object(sys, "argv", ["dfly-set", "pull_request_id", "12345"]):
                cli_state.set_cmd()

            mock_lookup.assert_called_once_with("pull_request_id", 12345, True)
