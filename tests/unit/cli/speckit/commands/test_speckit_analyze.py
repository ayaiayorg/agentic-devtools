"""Tests for speckit_analyze."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_analyze


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_analyze_delegates_to_run(mock_run):
    """speckit_analyze calls _run with 'analyze' and joined args."""
    speckit_analyze(["arg1"])
    mock_run.assert_called_once_with("analyze", "arg1")
