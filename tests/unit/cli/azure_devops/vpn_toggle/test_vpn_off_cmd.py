"""Tests for vpn_off_cmd function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import vpn_off_cmd


class TestVpnOffCmd:
    """Tests for vpn_off_cmd function."""

    def test_skips_when_pulse_not_installed(self, capsys):
        """Should print error and return early when Pulse Secure is not installed."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
            return_value=False,
        ):
            vpn_off_cmd()

        captured = capsys.readouterr()
        assert "not installed" in captured.out or "❌" in captured.out

    def test_skips_when_vpn_not_connected(self, capsys):
        """Should print info and return early when VPN is already disconnected."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
            return_value=True,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected",
                return_value=False,
            ):
                with patch(
                    "agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network",
                    return_value=False,
                ):
                    vpn_off_cmd()

        captured = capsys.readouterr()
        assert captured.out != "" or captured.err != ""

    def test_returns_early_when_vpn_url_not_configured(self, capsys):
        """Should print error and return early when VPN URL is None."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
            return_value=True,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected",
                return_value=True,
            ):
                with patch(
                    "agentic_devtools.cli.azure_devops.vpn_toggle.get_vpn_url_from_state",
                    return_value=None,
                ):
                    vpn_off_cmd()

        captured = capsys.readouterr()
        assert "VPN URL not configured" in captured.out
