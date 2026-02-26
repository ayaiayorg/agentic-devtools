"""Tests for speckit_constitution."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_constitution


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_constitution_delegates_to_run(mock_run):
    """speckit_constitution calls _run with 'constitution' and joined args."""
    speckit_constitution(["arg1"])
    mock_run.assert_called_once_with("constitution", "arg1")
