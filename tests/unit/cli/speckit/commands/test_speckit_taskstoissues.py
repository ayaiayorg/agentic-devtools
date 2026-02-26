"""Tests for speckit_taskstoissues."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_taskstoissues


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_taskstoissues_delegates_to_run(mock_run):
    """speckit_taskstoissues calls _run with 'taskstoissues' and joined args."""
    speckit_taskstoissues(["arg1"])
    mock_run.assert_called_once_with("taskstoissues", "arg1")
