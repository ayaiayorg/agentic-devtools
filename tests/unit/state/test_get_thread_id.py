"""Tests for agentic_devtools.state.get_thread_id."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_get_thread_id(temp_state_dir):
    """Test getting thread ID."""
    state.set_thread_id(67890)
    assert state.get_thread_id() == 67890
