"""Tests for azure_context_status_command function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_context.commands import azure_context_status_command


class TestAzureContextStatusCommand:
    """Tests for azure_context_status_command function."""

    def test_calls_show_all_contexts(self):
        """Should delegate to show_all_contexts to display context status."""
        with patch.object(sys, "argv", ["agdt-azure-context-status"]):
            with patch(
                "agentic_devtools.cli.azure_context.commands.show_all_contexts"
            ) as mock_show:
                azure_context_status_command()

        mock_show.assert_called_once()

    def test_prints_context_information(self, capsys):
        """Should print context information to stdout."""
        with patch.object(sys, "argv", ["agdt-azure-context-status"]):
            with patch(
                "agentic_devtools.cli.azure_context.commands.show_all_contexts",
                side_effect=lambda: print("Azure CLI Contexts:"),
            ):
                azure_context_status_command()

        captured = capsys.readouterr()
        assert "Azure CLI Contexts" in captured.out
