"""Tests for agentic_devtools.cli.state.clear_cmd."""

import sys
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


def test_clear_removes_all_state(temp_state_dir, clear_state_before):
    """Test that clear removes all state."""
    state.set_value("key1", "value1")
    state.set_value("key2", "value2")
    with patch.object(sys, "argv", ["agdt-clear"]):
        cli_state.clear_cmd()
    assert state.load_state() == {}
