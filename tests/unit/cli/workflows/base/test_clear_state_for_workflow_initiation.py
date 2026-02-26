"""Tests for clear_state_for_workflow_initiation function."""

from unittest.mock import patch

from agentic_devtools.cli.workflows.base import clear_state_for_workflow_initiation


class TestClearStateForWorkflowInitiation:
    """Tests for clear_state_for_workflow_initiation function."""

    def test_calls_clear_state(self, capsys):
        """Should call clear_state to remove all previous state."""
        with patch("agentic_devtools.cli.workflows.base.clear_state") as mock_clear:
            clear_state_for_workflow_initiation()

        mock_clear.assert_called_once()

    def test_prints_confirmation_message(self, capsys):
        """Should print a confirmation message after clearing state."""
        with patch("agentic_devtools.cli.workflows.base.clear_state"):
            clear_state_for_workflow_initiation()

        captured = capsys.readouterr()
        assert "Cleared" in captured.out or "cleared" in captured.out
