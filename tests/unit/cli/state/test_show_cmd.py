"""Tests for agentic_devtools.cli.state.show_cmd."""

import sys
from io import StringIO
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import state as cli_state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clear_state_before(temp_state_dir):
    """Clear state before each test."""
    state.clear_state()
    yield


def test_show_empty_state(temp_state_dir, clear_state_before):
    """Test showing empty state."""
    with patch.object(sys, "argv", ["agdt-show"]):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_state.show_cmd()
            assert "(empty state)" in mock_stdout.getvalue()


def test_show_state_with_values(temp_state_dir, clear_state_before):
    """Test showing state with values."""
    state.set_value("test", "value")
    with patch.object(sys, "argv", ["agdt-show"]):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_state.show_cmd()
            output = mock_stdout.getvalue()
            assert "test" in output
            assert "value" in output
