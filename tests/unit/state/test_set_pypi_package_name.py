"""Tests for agentic_devtools.state.set_pypi_package_name."""

from agentic_devtools import state


def test_set_pypi_package_name(temp_state_dir):
    """Test set_pypi_package_name stores the value."""
    state.set_pypi_package_name("my-package")
    assert state.get_pypi_package_name() == "my-package"
