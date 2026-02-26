"""Tests for speckit_specify."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_specify


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_specify_delegates_to_run(mock_run):
    """speckit_specify calls _run with 'specify' and joined args."""
    speckit_specify(["my", "feature"])
    mock_run.assert_called_once_with("specify", "my feature")


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_specify_no_args(mock_run):
    """speckit_specify with empty args passes empty string."""
    speckit_specify([])
    mock_run.assert_called_once_with("specify", "")
