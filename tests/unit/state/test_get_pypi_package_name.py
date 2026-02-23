"""Tests for agentic_devtools.state.get_pypi_package_name."""

import pytest

from agentic_devtools import state


def test_get_pypi_package_name_returns_none_when_not_set(temp_state_dir):
    """Test get_pypi_package_name returns None when not set."""
    assert state.get_pypi_package_name() is None


def test_get_pypi_package_name_returns_value(temp_state_dir):
    """Test get_pypi_package_name returns the stored package name."""
    state.set_pypi_package_name("my-package")
    assert state.get_pypi_package_name() == "my-package"


def test_get_pypi_package_name_required_raises_when_not_set(temp_state_dir):
    """Test get_pypi_package_name raises KeyError when required and not set."""
    with pytest.raises(KeyError):
        state.get_pypi_package_name(required=True)
