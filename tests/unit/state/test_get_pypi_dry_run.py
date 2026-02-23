"""Tests for agentic_devtools.state.get_pypi_dry_run."""

from agentic_devtools import state


def test_get_pypi_dry_run_returns_false_when_not_set(temp_state_dir):
    """Test get_pypi_dry_run returns False when not set."""
    assert state.get_pypi_dry_run() is False


def test_get_pypi_dry_run_returns_true(temp_state_dir):
    """Test get_pypi_dry_run returns True when set."""
    state.set_pypi_dry_run(True)
    assert state.get_pypi_dry_run() is True


def test_get_pypi_dry_run_returns_false(temp_state_dir):
    """Test get_pypi_dry_run returns False when set to False."""
    state.set_pypi_dry_run(False)
    assert state.get_pypi_dry_run() is False
