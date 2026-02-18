"""
Tests for network context detection module.
"""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.network.detection import (
    NetworkContext,
    detect_network_context,
    get_network_context_display,
)


class TestNetworkContext:
    """Tests for NetworkContext enum."""

    def test_enum_values(self):
        """Test NetworkContext enum has expected values."""
        assert NetworkContext.CORPORATE_NETWORK.value == "corporate_network"
        assert NetworkContext.REMOTE_WITH_VPN.value == "remote_with_vpn"
        assert NetworkContext.REMOTE_WITHOUT_VPN.value == "remote_without_vpn"
        assert NetworkContext.UNKNOWN.value == "unknown"


class TestDetectNetworkContext:
    """Tests for detect_network_context function."""

    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected")
    def test_remote_with_vpn(self, mock_vpn_connected):
        """Test detection when VPN is connected."""
        mock_vpn_connected.return_value = True

        context, description = detect_network_context()

        assert context == NetworkContext.REMOTE_WITH_VPN
        assert "Remote with VPN connected" in description
        mock_vpn_connected.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_corporate_network(self, mock_corporate, mock_vpn_connected):
        """Test detection when on corporate network without VPN."""
        mock_vpn_connected.return_value = False
        mock_corporate.return_value = True

        context, description = detect_network_context()

        assert context == NetworkContext.CORPORATE_NETWORK
        assert "corporate network" in description.lower()
        mock_vpn_connected.assert_called_once()
        mock_corporate.assert_called_once()

    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_remote_without_vpn(self, mock_corporate, mock_vpn_connected):
        """Test detection when remote without VPN."""
        mock_vpn_connected.return_value = False
        mock_corporate.return_value = False

        context, description = detect_network_context()

        assert context == NetworkContext.REMOTE_WITHOUT_VPN
        assert "Remote without VPN" in description
        mock_vpn_connected.assert_called_once()
        mock_corporate.assert_called_once()

    def test_import_error(self):
        """Test handling of import errors (non-Windows platform)."""
        # Mock the import to raise ImportError
        with patch.dict("sys.modules", {"agentic_devtools.cli.azure_devops.vpn_toggle": None}):
            context, description = detect_network_context()

            assert context == NetworkContext.UNKNOWN
            assert "not available" in description.lower()

    @patch("agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected")
    def test_exception_handling(self, mock_vpn_connected):
        """Test handling of unexpected exceptions."""
        mock_vpn_connected.side_effect = Exception("Unexpected error")

        context, description = detect_network_context()

        assert context == NetworkContext.UNKNOWN
        assert "failed" in description.lower()


class TestGetNetworkContextDisplay:
    """Tests for get_network_context_display function."""

    def test_corporate_network_display(self):
        """Test display for corporate network context."""
        display = get_network_context_display(
            NetworkContext.CORPORATE_NETWORK,
            "On corporate network",
        )

        assert "🏢" in display
        assert "On corporate network" in display
        assert "skipped automatically" in display

    def test_remote_with_vpn_display(self):
        """Test display for remote with VPN context."""
        display = get_network_context_display(
            NetworkContext.REMOTE_WITH_VPN,
            "VPN connected",
        )

        assert "🔌" in display
        assert "VPN connected" in display
        assert "agdt-vpn-off" in display

    def test_remote_without_vpn_display(self):
        """Test display for remote without VPN context."""
        display = get_network_context_display(
            NetworkContext.REMOTE_WITHOUT_VPN,
            "No VPN",
        )

        assert "📡" in display
        assert "No VPN" in display
        assert "agdt-vpn-on" in display

    def test_unknown_display(self):
        """Test display for unknown context."""
        display = get_network_context_display(
            NetworkContext.UNKNOWN,
            "Unknown state",
        )

        assert "❓" in display
        assert "Unknown state" in display
        assert "not be available" in display
