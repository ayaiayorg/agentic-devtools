"""Tests for agentic_devtools.cli.git.core.get_commit_message."""

import pytest

from agentic_devtools import state
from agentic_devtools.cli.git import core


class TestGetCommitMessage:
    """Tests for commit message retrieval."""

    def test_get_commit_message_returns_value(self, temp_state_dir, clear_state_before):
        """Test getting commit message from state."""
        state.set_value("commit_message", "Test commit")
        message = core.get_commit_message()
        assert message == "Test commit"

    def test_get_commit_message_missing_exits(self, temp_state_dir, clear_state_before):
        """Test that missing commit message causes exit."""
        with pytest.raises(SystemExit) as exc_info:
            core.get_commit_message()
        assert exc_info.value.code == 1

    def test_get_multiline_commit_message(self, temp_state_dir, clear_state_before):
        """Test getting multiline commit message."""
        multiline = "Title\n\n- Change 1\n- Change 2"
        state.set_value("commit_message", multiline)
        message = core.get_commit_message()
        assert message == multiline

    def test_get_commit_message_with_special_characters(self, temp_state_dir, clear_state_before):
        """Test commit message with special characters works without tokens."""
        special = 'feature([DFLY-1234](https://jira.swica.ch)): test\'s "quotes" & more!'
        state.set_value("commit_message", special)
        message = core.get_commit_message()
        assert message == special
