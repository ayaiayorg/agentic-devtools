"""
Tests for network CLI commands.
"""

from io import StringIO
from unittest.mock import patch

from agentic_devtools.cli.network.commands import network_status_cmd
from agentic_devtools.cli.network.detection import NetworkContext


class TestNetworkStatusCmd:
    """Tests for network_status_cmd function."""

    @patch("agentic_devtools.cli.network.commands.detect_network_context")
    @patch("sys.stdout", new_callable=StringIO)
    def test_network_status_corporate(self, mock_stdout, mock_detect):
        """Test network status command with corporate network."""
        mock_detect.return_value = (
            NetworkContext.CORPORATE_NETWORK,
            "On corporate network",
        )

        network_status_cmd()

        output = mock_stdout.getvalue()
        assert "Detecting network context" in output
        assert "Network Status" in output
        assert "🏢" in output
        assert "On corporate network" in output

    @patch("agentic_devtools.cli.network.commands.detect_network_context")
    @patch("sys.stdout", new_callable=StringIO)
    def test_network_status_vpn(self, mock_stdout, mock_detect):
        """Test network status command with VPN connected."""
        mock_detect.return_value = (
            NetworkContext.REMOTE_WITH_VPN,
            "VPN connected",
        )

        network_status_cmd()

        output = mock_stdout.getvalue()
        assert "Detecting network context" in output
        assert "Network Status" in output
        assert "🔌" in output
        assert "VPN connected" in output

    @patch("agentic_devtools.cli.network.commands.detect_network_context")
    @patch("sys.stdout", new_callable=StringIO)
    def test_network_status_remote(self, mock_stdout, mock_detect):
        """Test network status command without VPN."""
        mock_detect.return_value = (
            NetworkContext.REMOTE_WITHOUT_VPN,
            "No VPN",
        )

        network_status_cmd()

        output = mock_stdout.getvalue()
        assert "Detecting network context" in output
        assert "Network Status" in output
        assert "📡" in output
        assert "No VPN" in output
