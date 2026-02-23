"""Tests for agentic_devtools.state.set_pypi_repository."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_set_pypi_repository(temp_state_dir):
    """Test set_pypi_repository stores the value."""
    state.set_pypi_repository("testpypi")
    assert state.get_pypi_repository() == "testpypi"
