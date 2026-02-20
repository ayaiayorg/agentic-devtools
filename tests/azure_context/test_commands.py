"""
Tests for Azure context CLI commands.
"""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_context.commands import (
    azure_context_current_command,
    azure_context_ensure_login_command,
    azure_context_status_command,
    azure_context_use_command,
)
from agentic_devtools.cli.azure_context.config import AzureContext


class TestAzureContextUseCommand:
    """Tests for azure_context_use_command CLI function."""

    @patch("agentic_devtools.cli.azure_context.commands.switch_context")
    @patch("builtins.print")
    def test_switches_to_devops_context(self, mock_print, mock_switch):
        """Test switching to DevOps context."""
        with patch("sys.argv", ["agdt-azure-context-use", "devops"]):
            azure_context_use_command()

        mock_switch.assert_called_once_with(AzureContext.DEVOPS)

    @patch("agentic_devtools.cli.azure_context.commands.switch_context")
    @patch("builtins.print")
    def test_switches_to_resources_context(self, mock_print, mock_switch):
        """Test switching to resources context."""
        with patch("sys.argv", ["agdt-azure-context-use", "resources"]):
            azure_context_use_command()

        mock_switch.assert_called_once_with(AzureContext.AZURE_RESOURCES)

    @patch("agentic_devtools.cli.azure_context.commands.switch_context")
    @patch("agentic_devtools.cli.azure_context.commands.ensure_logged_in")
    @patch("builtins.print")
    def test_ensure_login_flag(self, mock_print, mock_ensure, mock_switch):
        """Test --ensure-login flag triggers login check."""
        mock_ensure.return_value = True

        with patch("sys.argv", ["agdt-azure-context-use", "devops", "--ensure-login"]):
            azure_context_use_command()

        mock_switch.assert_called_once_with(AzureContext.DEVOPS)
        mock_ensure.assert_called_once_with(AzureContext.DEVOPS)

    @patch("agentic_devtools.cli.azure_context.commands.switch_context")
    @patch("agentic_devtools.cli.azure_context.commands.ensure_logged_in")
    @patch("builtins.print")
    def test_ensure_login_failure_exits(self, mock_print, mock_ensure, mock_switch):
        """Test that login failure exits with error code."""
        mock_ensure.return_value = False

        with patch("sys.argv", ["agdt-azure-context-use", "devops", "--ensure-login"]):
            with pytest.raises(SystemExit) as exc_info:
                azure_context_use_command()

        assert exc_info.value.code == 1

    @patch("builtins.print")
    def test_invalid_context_exits(self, mock_print):
        """Test that invalid context name exits with error."""
        with patch("sys.argv", ["agdt-azure-context-use", "invalid"]):
            # argparse will handle this and exit
            with pytest.raises(SystemExit):
                azure_context_use_command()


class TestAzureContextStatusCommand:
    """Tests for azure_context_status_command CLI function."""

    @patch("agentic_devtools.cli.azure_context.commands.show_all_contexts")
    def test_calls_show_all_contexts(self, mock_show):
        """Test that status command calls show_all_contexts."""
        with patch("sys.argv", ["agdt-azure-context-status"]):
            azure_context_status_command()

        mock_show.assert_called_once()


class TestAzureContextCurrentCommand:
    """Tests for azure_context_current_command CLI function."""

    @patch("agentic_devtools.cli.azure_context.commands.get_current_context")
    @patch("builtins.print")
    def test_displays_current_context(self, mock_print, mock_get_current):
        """Test displays current context when set."""
        mock_get_current.return_value = AzureContext.DEVOPS

        with patch("sys.argv", ["agdt-azure-context-current"]):
            azure_context_current_command()

        # Should print the current context
        printed = " ".join(str(call) for call in mock_print.call_args_list)
        assert "devops" in printed.lower()

    @patch("agentic_devtools.cli.azure_context.commands.get_current_context")
    @patch("builtins.print")
    def test_displays_message_when_no_context(self, mock_print, mock_get_current):
        """Test displays message when no context is set."""
        mock_get_current.return_value = None

        with patch("sys.argv", ["agdt-azure-context-current"]):
            azure_context_current_command()

        # Should print message about no context
        printed = " ".join(str(call) for call in mock_print.call_args_list)
        assert "no" in printed.lower() or "not set" in printed.lower()


class TestAzureContextEnsureLoginCommand:
    """Tests for azure_context_ensure_login_command CLI function."""

    @patch("agentic_devtools.cli.azure_context.commands.ensure_logged_in")
    @patch("builtins.print")
    def test_ensures_login_for_specified_context(self, mock_print, mock_ensure):
        """Test ensures login for explicitly specified context."""
        mock_ensure.return_value = True

        with patch("sys.argv", ["agdt-azure-context-ensure-login", "devops"]):
            azure_context_ensure_login_command()

        mock_ensure.assert_called_once_with(AzureContext.DEVOPS)

    @patch("agentic_devtools.cli.azure_context.commands.get_current_context")
    @patch("agentic_devtools.cli.azure_context.commands.ensure_logged_in")
    @patch("builtins.print")
    def test_uses_current_context_when_not_specified(self, mock_print, mock_ensure, mock_get_current):
        """Test uses current context when none specified."""
        mock_get_current.return_value = AzureContext.DEVOPS
        mock_ensure.return_value = True

        with patch("sys.argv", ["agdt-azure-context-ensure-login"]):
            azure_context_ensure_login_command()

        mock_ensure.assert_called_once_with(AzureContext.DEVOPS)

    @patch("agentic_devtools.cli.azure_context.commands.get_current_context")
    @patch("builtins.print")
    def test_exits_when_no_current_context(self, mock_print, mock_get_current):
        """Test exits with error when no current context and none specified."""
        mock_get_current.return_value = None

        with patch("sys.argv", ["agdt-azure-context-ensure-login"]):
            with pytest.raises(SystemExit) as exc_info:
                azure_context_ensure_login_command()

        assert exc_info.value.code == 1

    @patch("agentic_devtools.cli.azure_context.commands.ensure_logged_in")
    @patch("builtins.print")
    def test_exits_on_login_failure(self, mock_print, mock_ensure):
        """Test exits with error code when login fails."""
        mock_ensure.return_value = False

        with patch("sys.argv", ["agdt-azure-context-ensure-login", "devops"]):
            with pytest.raises(SystemExit) as exc_info:
                azure_context_ensure_login_command()

        assert exc_info.value.code == 1
