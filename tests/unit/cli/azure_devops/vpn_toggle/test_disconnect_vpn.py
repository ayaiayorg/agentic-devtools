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



class TestDisconnectVpn:
    """Tests for disconnect_vpn function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_fails_when_not_installed(self, mock_installed):
        """Test returns failure when Pulse Secure not installed."""
        mock_installed.return_value = False

        success, msg = disconnect_vpn()

        assert success is False
        assert "not installed" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("time.sleep")
    def test_successful_disconnect(self, mock_sleep, mock_installed, mock_cmd, mock_vpn):
        """Test successful VPN disconnect."""
        mock_installed.return_value = True
        mock_cmd.return_value = (True, "Suspended", 0)  # 3-tuple: success, output, return_code
        mock_vpn.side_effect = [True, False]  # Connected, then disconnected

        success, msg = disconnect_vpn(max_wait_seconds=5, check_interval=1.0)

        assert success is True
        assert "verified disconnected" in msg.lower() or "suspend" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_command_failure(self, mock_installed, mock_cmd):
        """Test handles command failure."""
        mock_installed.return_value = True
        mock_cmd.return_value = (False, "Command failed", 1)  # 3-tuple: success, output, return_code

        success, msg = disconnect_vpn()

        assert success is False
        assert "failed" in msg.lower()
