"""Tests for speckit_tasks."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_tasks


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_tasks_delegates_to_run(mock_run):
    """speckit_tasks calls _run with 'tasks' and joined args."""
    speckit_tasks(["arg1"])
    mock_run.assert_called_once_with("tasks", "arg1")
