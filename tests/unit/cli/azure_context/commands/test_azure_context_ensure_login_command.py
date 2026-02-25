"""Tests for azure_context_ensure_login_command function."""

import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_context.commands import azure_context_ensure_login_command
from agentic_devtools.cli.azure_context.config import AzureContext


class TestAzureContextEnsureLoginCommand:
    """Tests for azure_context_ensure_login_command function."""

    def test_ensures_login_for_specified_context(self):
        """Should call ensure_logged_in for the specified context argument."""
        with patch.object(sys, "argv", ["agdt-azure-context-ensure-login", "devops"]):
            with patch(
                "agentic_devtools.cli.azure_context.commands.ensure_logged_in",
                return_value=True,
            ) as mock_ensure:
                azure_context_ensure_login_command()

        mock_ensure.assert_called_once_with(AzureContext.DEVOPS)

    def test_prints_error_when_no_context_set(self, capsys):
        """Should print error message when no context is active and none given."""
        import pytest

        with patch.object(sys, "argv", ["agdt-azure-context-ensure-login"]):
            with patch(
                "agentic_devtools.cli.azure_context.commands.get_current_context",
                return_value=None,
            ):
                with pytest.raises(SystemExit):
                    azure_context_ensure_login_command()

        captured = capsys.readouterr()
        assert "No Azure context" in captured.out or "not" in captured.out.lower()
