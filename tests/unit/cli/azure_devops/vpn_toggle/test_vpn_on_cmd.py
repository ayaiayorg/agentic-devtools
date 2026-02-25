"""Tests for vpn_on_cmd function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import vpn_on_cmd


class TestVpnOnCmd:
    """Tests for vpn_on_cmd function."""

    def test_skips_when_on_corporate_network(self, capsys):
        """Should print info message and return early when on corporate network."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network",
            return_value=True,
        ):
            vpn_on_cmd()

        captured = capsys.readouterr()
        assert "corporate" in captured.out.lower() or "office" in captured.out.lower()

    def test_skips_when_pulse_not_installed(self, capsys):
        """Should print error and return early when Pulse Secure is not installed."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network",
            return_value=False,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
                return_value=False,
            ):
                vpn_on_cmd()

        captured = capsys.readouterr()
        assert "not installed" in captured.out or "❌" in captured.out

    def test_skips_when_vpn_already_connected(self, capsys):
        """Should print info and return early when VPN is already connected."""
        with patch(
            "agentic_devtools.cli.azure_devops.vpn_toggle.is_on_corporate_network",
            return_value=False,
        ):
            with patch(
                "agentic_devtools.cli.azure_devops.vpn_toggle.is_pulse_secure_installed",
                return_value=True,
            ):
                with patch(
                    "agentic_devtools.cli.azure_devops.vpn_toggle.is_vpn_connected",
                    return_value=True,
                ):
                    vpn_on_cmd()

        captured = capsys.readouterr()
        assert "already connected" in captured.out or "ℹ️" in captured.out
