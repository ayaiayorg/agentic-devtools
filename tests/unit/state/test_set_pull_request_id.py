"""Tests for agentic_devtools.state.set_pull_request_id."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_set_pull_request_id(temp_state_dir):
    """Test setting pull request ID."""
    state.set_pull_request_id(12345)
    assert state.get_value("pull_request_id") == 12345
