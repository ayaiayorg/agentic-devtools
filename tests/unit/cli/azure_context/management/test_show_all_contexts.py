"""Tests for show_all_contexts function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_context.config import AzureContext
from agentic_devtools.cli.azure_context.management import show_all_contexts


class TestShowAllContexts:
    """Tests for show_all_contexts function."""

    def test_prints_all_context_names(self, capsys):
        """Should print all available context names to stdout."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_current_context",
            return_value=None,
        ):
            with patch(
                "agentic_devtools.cli.azure_context.management.check_login_status",
                return_value=(False, None, "Not logged in"),
            ):
                show_all_contexts()

        captured = capsys.readouterr()
        # Both context names should appear in output
        assert "devops" in captured.out
        assert "resources" in captured.out

    def test_marks_active_context(self, capsys):
        """Should mark the currently active context with [ACTIVE]."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_current_context",
            return_value=AzureContext.DEVOPS,
        ):
            with patch(
                "agentic_devtools.cli.azure_context.management.check_login_status",
                return_value=(True, "user@company.com", None),
            ):
                show_all_contexts()

        captured = capsys.readouterr()
        assert "ACTIVE" in captured.out

    def test_prints_header(self, capsys):
        """Should print an Azure CLI Contexts header."""
        with patch(
            "agentic_devtools.cli.azure_context.management.get_current_context",
            return_value=None,
        ):
            with patch(
                "agentic_devtools.cli.azure_context.management.check_login_status",
                return_value=(False, None, "Not logged in"),
            ):
                show_all_contexts()

        captured = capsys.readouterr()
        assert "Azure CLI Contexts" in captured.out
