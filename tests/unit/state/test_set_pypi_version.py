"""Tests for agentic_devtools.state.set_pypi_version."""

from agentic_devtools import state


def test_set_pypi_version(temp_state_dir):
    """Test set_pypi_version stores the value."""
    state.set_pypi_version("1.2.3")
    assert state.get_pypi_version() == "1.2.3"
