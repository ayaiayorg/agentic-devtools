"""Tests for speckit_plan."""

from unittest.mock import patch

from agentic_devtools.cli.speckit.commands import speckit_plan


@patch("agentic_devtools.cli.speckit.commands._run")
def test_speckit_plan_delegates_to_run(mock_run):
    """speckit_plan calls _run with 'plan' and joined args."""
    speckit_plan(["my", "plan"])
    mock_run.assert_called_once_with("plan", "my plan")
