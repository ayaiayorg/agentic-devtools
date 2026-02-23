"""Tests for agentic_devtools.state.get_all_keys."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_get_all_keys(temp_state_dir):
    """Test getting all keys in state."""
    state.set_value("key1", "value1")
    state.set_value("key2", "value2")
    keys = state.get_all_keys()
    assert set(keys) == {"key1", "key2"}
