"""Tests for speckit_checklist."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_checklist


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_checklist_delegates_to_run(mock_run):
    """speckit_checklist calls _run with 'checklist' and joined args."""
    speckit_checklist(["arg1"])
    mock_run.assert_called_once_with("checklist", "arg1")
