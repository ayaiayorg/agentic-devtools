"""Tests for agentic_devtools.cli.state.clear_workflow_cmd."""

import sys
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli import state as cli_state


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        yield tmp_path


def test_clear_workflow_cmd_no_active_workflow(temp_state_dir, capsys):
    """Test clear_workflow_cmd when no workflow is active."""
    with patch.object(sys, "argv", ["agdt-clear-workflow"]):
        cli_state.clear_workflow_cmd()
    captured = capsys.readouterr()
    assert "No workflow" in captured.out


def test_clear_workflow_cmd_clears_active_workflow(temp_state_dir, capsys):
    """Test clear_workflow_cmd clears the active workflow."""
    state.set_workflow_state(name="test-workflow", status="in-progress")
    with patch.object(sys, "argv", ["agdt-clear-workflow"]):
        cli_state.clear_workflow_cmd()
    assert state.get_workflow_state() is None
    captured = capsys.readouterr()
    assert "test-workflow" in captured.out
