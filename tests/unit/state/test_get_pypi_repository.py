"""Tests for agentic_devtools.state.get_pypi_repository."""

import pytest

from agentic_devtools import state


def test_get_pypi_repository_returns_none_when_not_set(temp_state_dir):
    """Test get_pypi_repository returns None when not set."""
    assert state.get_pypi_repository() is None


def test_get_pypi_repository_returns_value(temp_state_dir):
    """Test get_pypi_repository returns the stored repository."""
    state.set_pypi_repository("testpypi")
    assert state.get_pypi_repository() == "testpypi"


def test_get_pypi_repository_required_raises_when_not_set(temp_state_dir):
    """Test get_pypi_repository raises KeyError when required and not set."""
    with pytest.raises(KeyError):
        state.get_pypi_repository(required=True)
