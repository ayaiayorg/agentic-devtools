"""Tests for network_status_cmd function."""

from unittest.mock import patch

from agentic_devtools.cli.network.commands import network_status_cmd
from agentic_devtools.cli.network.detection import NetworkContext


class TestNetworkStatusCmd:
    """Tests for network_status_cmd function."""

    def test_prints_network_status_header(self, capsys):
        """Should print 'Network Status' header to stdout."""
        with patch(
            "agentic_devtools.cli.network.commands.detect_network_context",
            return_value=(NetworkContext.REMOTE_WITH_VPN, "VPN connected"),
        ):
            with patch(
                "agentic_devtools.cli.network.commands.get_network_context_display",
                return_value="🔌 VPN connected\n   Use agdt-vpn-off to disconnect",
            ):
                network_status_cmd()

        captured = capsys.readouterr()
        assert "Network Status" in captured.out

    def test_prints_display_output(self, capsys):
        """Should print the formatted display string from get_network_context_display."""
        display_text = "🏢 In office - VPN not needed"

        with patch(
            "agentic_devtools.cli.network.commands.detect_network_context",
            return_value=(NetworkContext.CORPORATE_NETWORK, "In office"),
        ):
            with patch(
                "agentic_devtools.cli.network.commands.get_network_context_display",
                return_value=display_text,
            ):
                network_status_cmd()

        captured = capsys.readouterr()
        assert "🏢" in captured.out

    def test_calls_detect_network_context(self):
        """Should call detect_network_context to get the current context."""
        with patch(
            "agentic_devtools.cli.network.commands.detect_network_context",
            return_value=(NetworkContext.UNKNOWN, "Unknown"),
        ) as mock_detect:
            with patch(
                "agentic_devtools.cli.network.commands.get_network_context_display",
                return_value="❓ Unknown",
            ):
                network_status_cmd()

        mock_detect.assert_called_once()
