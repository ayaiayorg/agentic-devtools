"""Tests for agentic_devtools.state.load_state_locked."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_load_state_locked(temp_state_dir):
    """Test load_state_locked returns current state."""
    state.save_state({"key": "value"})

    loaded = state.load_state_locked()
    assert loaded == {"key": "value"}
