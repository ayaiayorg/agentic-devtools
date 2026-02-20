"""
Tests for the VPN wrapper decorator for Jira commands.

Tests verify the with_jira_vpn_context decorator properly wraps functions
and handles VPN management gracefully even when dependencies are unavailable.
"""

from unittest.mock import patch

from agentic_devtools.cli.jira.vpn_wrapper import with_jira_vpn_context


class TestWithJiraVpnContextIntegration:
    """Integration tests for the VPN wrapper with mocked VPN toggle module."""

    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_decorator_works_on_corporate_network(self, mock_corp):
        """Test decorator works when on corporate network."""
        mock_corp.return_value = True

        @with_jira_vpn_context
        def get_data():
            return {"key": "value"}

        result = get_data()

        assert result == {"key": "value"}
        mock_corp.assert_called()

    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.smart_connect_vpn")
    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_decorator_connects_and_disconnects_vpn(
        self, mock_corp, mock_installed, mock_vpn, mock_connect, mock_disconnect
    ):
        """Test decorator connects VPN before and disconnects after function call."""
        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = False  # VPN is off
        mock_connect.return_value = (True, "Connected")
        mock_disconnect.return_value = (True, "Disconnected")

        call_order = []

        @with_jira_vpn_context
        def my_function():
            call_order.append("function")
            return "result"

        result = my_function()

        assert result == "result"
        mock_connect.assert_called_once()
        mock_disconnect.assert_called_once()
