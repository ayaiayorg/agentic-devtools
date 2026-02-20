"""Tests for agentic_devtools.state.save_state_locked."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_save_state_locked(temp_state_dir):
    """Test save_state_locked saves state and returns path."""
    path = state.save_state_locked({"key": "value"})

    assert path.exists()
    loaded = state.load_state()
    assert loaded == {"key": "value"}
