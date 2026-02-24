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


def test_get_pypi_dry_run_string_true(temp_state_dir):
    """Test get_pypi_dry_run coerces string 'true' to True."""
    state.set_value("pypi.dry_run", "true")
    assert state.get_pypi_dry_run() is True


def test_get_pypi_dry_run_string_yes(temp_state_dir):
    """Test get_pypi_dry_run coerces string 'yes' to True."""
    state.set_value("pypi.dry_run", "yes")
    assert state.get_pypi_dry_run() is True


def test_get_pypi_dry_run_string_1(temp_state_dir):
    """Test get_pypi_dry_run coerces string '1' to True."""
    state.set_value("pypi.dry_run", "1")
    assert state.get_pypi_dry_run() is True


def test_get_pypi_dry_run_string_false(temp_state_dir):
    """Test get_pypi_dry_run coerces string 'false' to False."""
    state.set_value("pypi.dry_run", "false")
    assert state.get_pypi_dry_run() is False


def test_get_pypi_dry_run_string_no(temp_state_dir):
    """Test get_pypi_dry_run coerces string 'no' to False."""
    state.set_value("pypi.dry_run", "no")
    assert state.get_pypi_dry_run() is False
