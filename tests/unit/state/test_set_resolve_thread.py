"""Tests for agentic_devtools.state.set_resolve_thread."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_set_resolve_thread_true(temp_state_dir):
    """Test setting resolve_thread to True."""
    state.set_resolve_thread(True)
    assert state.should_resolve_thread() is True


def test_set_resolve_thread_false(temp_state_dir):
    """Test setting resolve_thread to False."""
    state.set_resolve_thread(False)
    assert state.should_resolve_thread() is False
