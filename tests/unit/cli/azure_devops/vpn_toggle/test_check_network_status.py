"""
Tests for VPN toggle utilities.

Tests verify VPN detection, corporate network detection,
and the VpnToggleContext manager.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
    CORPORATE_NETWORK_TEST_HOST,
    DEFAULT_VPN_URL,
    PULSE_LAUNCHER_PATH,
    JiraVpnContext,
    NetworkStatus,
    VpnToggleContext,
    _run_pulse_command,
    check_network_status,
    disconnect_vpn,
    get_vpn_url_from_state,
    is_on_corporate_network,
    is_pulse_secure_installed,
    is_vpn_connected,
    reconnect_vpn,
)



class TestCheckNetworkStatus:
    """Tests for check_network_status function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    def test_vpn_connected_status(self, mock_vpn):
        """Test returns VPN_CONNECTED when VPN is on."""
        mock_vpn.return_value = True

        status, msg = check_network_status()

        assert status == NetworkStatus.VPN_CONNECTED
        assert "VPN is connected" in msg

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_corporate_network_status(self, mock_corp, mock_vpn):
        """Test returns CORPORATE_NETWORK_NO_VPN when in office."""
        mock_vpn.return_value = False
        mock_corp.return_value = True

        status, msg = check_network_status()

        assert status == NetworkStatus.CORPORATE_NETWORK_NO_VPN
        assert "corporate network" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_external_access_ok(self, mock_corp, mock_vpn):
        """Test returns EXTERNAL_ACCESS_OK when not on VPN or corp network."""
        mock_vpn.return_value = False
        mock_corp.return_value = False

        status, msg = check_network_status()

        assert status == NetworkStatus.EXTERNAL_ACCESS_OK

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    def test_verbose_output(self, mock_vpn, capsys):
        """Test verbose mode prints status."""
        mock_vpn.return_value = True

        check_network_status(verbose=True)

        captured = capsys.readouterr()
        assert "🔌" in captured.out
