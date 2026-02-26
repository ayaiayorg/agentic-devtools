"""Tests for azure_context_use_command function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_context.commands import azure_context_use_command


class TestAzureContextUseCommand:
    """Tests for azure_context_use_command function."""

    def test_switches_to_devops_context(self, capsys):
        """Should switch to the devops context and print confirmation."""
        with patch.object(sys, "argv", ["agdt-azure-context-use", "devops"]):
            with patch("agentic_devtools.cli.azure_context.commands.switch_context") as mock_switch:
                azure_context_use_command()

        mock_switch.assert_called_once()
        captured = capsys.readouterr()
        assert "devops" in captured.out

    def test_switches_to_resources_context(self, capsys):
        """Should switch to the resources context and print confirmation."""
        with patch.object(sys, "argv", ["agdt-azure-context-use", "resources"]):
            with patch("agentic_devtools.cli.azure_context.commands.switch_context") as mock_switch:
                azure_context_use_command()

        mock_switch.assert_called_once()
        captured = capsys.readouterr()
        assert "resources" in captured.out
