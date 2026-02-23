"""Tests for agentic_devtools.state.get_pypi_version."""

import pytest

from agentic_devtools import state


def test_get_pypi_version_returns_none_when_not_set(temp_state_dir):
    """Test get_pypi_version returns None when not set."""
    assert state.get_pypi_version() is None


def test_get_pypi_version_returns_value(temp_state_dir):
    """Test get_pypi_version returns the stored version."""
    state.set_pypi_version("1.2.3")
    assert state.get_pypi_version() == "1.2.3"


def test_get_pypi_version_required_raises_when_not_set(temp_state_dir):
    """Test get_pypi_version raises KeyError when required and not set."""
    with pytest.raises(KeyError):
        state.get_pypi_version(required=True)
