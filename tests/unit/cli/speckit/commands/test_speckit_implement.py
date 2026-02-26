"""Tests for speckit_implement."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_implement


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_implement_delegates_to_run(mock_run):
    """speckit_implement calls _run with 'implement' and joined args."""
    speckit_implement(["arg1"])
    mock_run.assert_called_once_with("implement", "arg1")
