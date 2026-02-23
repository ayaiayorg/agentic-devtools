"""Tests for agentic_devtools.state.clear_state."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_clear_state(temp_state_dir):
    """Test clearing all state."""
    state.set_value("key1", "value1")
    state.set_value("key2", "value2")
    state.clear_state()
    assert state.load_state() == {}
