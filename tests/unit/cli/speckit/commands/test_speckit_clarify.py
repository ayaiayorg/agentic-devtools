"""Tests for speckit_clarify."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_clarify


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_clarify_delegates_to_run(mock_run):
    """speckit_clarify calls _run with 'clarify' and joined args."""
    speckit_clarify(["arg1"])
    mock_run.assert_called_once_with("clarify", "arg1")
