"""Tests for agentic_devtools.state.set_dry_run."""

from agentic_devtools import state


def test_set_dry_run_true(temp_state_dir):
    """Test setting dry_run to True."""
    state.set_dry_run(True)
    assert state.is_dry_run() is True


def test_set_dry_run_false(temp_state_dir):
    """Test setting dry_run to False."""
    state.set_dry_run(False)
    assert state.is_dry_run() is False
