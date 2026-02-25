"""Tests for azure_context_current_command function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_context.commands import azure_context_current_command
from agentic_devtools.cli.azure_context.config import AzureContext


class TestAzureContextCurrentCommand:
    """Tests for azure_context_current_command function."""

    def test_prints_current_context_when_set(self, capsys):
        """Should print the current context name when one is active."""
        with patch.object(sys, "argv", ["agdt-azure-context-current"]):
            with patch(
                "agentic_devtools.cli.azure_context.commands.get_current_context",
                return_value=AzureContext.DEVOPS,
            ):
                azure_context_current_command()

        captured = capsys.readouterr()
        assert "devops" in captured.out

    def test_prints_no_context_message_when_none_set(self, capsys):
        """Should print a helpful message when no context is active."""
        with patch.object(sys, "argv", ["agdt-azure-context-current"]):
            with patch(
                "agentic_devtools.cli.azure_context.commands.get_current_context",
                return_value=None,
            ):
                azure_context_current_command()

        captured = capsys.readouterr()
        assert "No Azure context" in captured.out or "not" in captured.out.lower()
