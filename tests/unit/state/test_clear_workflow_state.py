"""Tests for agentic_devtools.state.clear_workflow_state."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_clear_workflow_state(temp_state_dir):
    """Test clearing workflow state."""
    state.set_workflow_state(name="test-workflow", status="in-progress")
    assert state.get_workflow_state() is not None

    state.clear_workflow_state()
    assert state.get_workflow_state() is None
