"""Tests for agentic_devtools.state.set_pypi_repository."""

from agentic_devtools import state


def test_set_pypi_repository(temp_state_dir):
    """Test set_pypi_repository stores the value."""
    state.set_pypi_repository("testpypi")
    assert state.get_pypi_repository() == "testpypi"
