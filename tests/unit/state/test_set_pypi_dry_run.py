"""Tests for agentic_devtools.state.set_pypi_dry_run."""

from unittest.mock import patch

import pytest

from agentic_devtools import state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_set_pypi_dry_run_true(temp_state_dir):
    """Test set_pypi_dry_run stores True."""
    state.set_pypi_dry_run(True)
    assert state.get_pypi_dry_run() is True


def test_set_pypi_dry_run_false(temp_state_dir):
    """Test set_pypi_dry_run stores False."""
    state.set_pypi_dry_run(False)
    assert state.get_pypi_dry_run() is False
