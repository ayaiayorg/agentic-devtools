"""Tests for agentic_devtools.cli.state.get_workflow_cmd."""

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


def test_get_workflow_cmd_no_active_workflow(temp_state_dir, capsys):
    """Test get_workflow_cmd when no workflow is active."""
    with patch.object(sys, "argv", ["agdt-get-workflow"]):
        cli_state.get_workflow_cmd()
    captured = capsys.readouterr()
    assert "No workflow" in captured.out


def test_get_workflow_cmd_active_workflow(temp_state_dir):
    """Test get_workflow_cmd shows active workflow as JSON."""
    state.set_workflow_state(name="test-workflow", status="in-progress", step="step-1")
    with patch.object(sys, "argv", ["agdt-get-workflow"]):
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            cli_state.get_workflow_cmd()
            output = mock_stdout.getvalue()
            assert "test-workflow" in output
            assert "in-progress" in output
