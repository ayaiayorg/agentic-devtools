"""Tests for vpn_status_cmd function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import NetworkStatus, vpn_status_cmd


class TestVpnStatusCmd:
    """Tests for vpn_status_cmd function."""

    def test_prints_not_installed_when_pulse_missing(self, capsys):
        """Should print info when Pulse Secure is not installed."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
            return_value=False,
        ):
            vpn_status_cmd()

        captured = capsys.readouterr()
        assert "not installed" in captured.out or "ℹ️" in captured.out

    def test_prints_vpn_connected_status(self, capsys):
        """Should print VPN connected message when status is VPN_CONNECTED."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
            return_value=True,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.vpn_toggle.check_network_status",
                return_value=(NetworkStatus.VPN_CONNECTED, "VPN connected"),
            ):
                vpn_status_cmd()

        captured = capsys.readouterr()
        assert "CONNECTED" in captured.out or "🔌" in captured.out

    def test_prints_vpn_disconnected_status(self, capsys):
        """Should print VPN disconnected message when external access is OK."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
            return_value=True,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.vpn_toggle.check_network_status",
                return_value=(NetworkStatus.EXTERNAL_ACCESS_OK, "VPN off"),
            ):
                vpn_status_cmd()

        captured = capsys.readouterr()
        assert "DISCONNECTED" in captured.out or "✅" in captured.out
