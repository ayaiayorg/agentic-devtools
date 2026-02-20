"""
Tests for VPN toggle utilities.

Tests verify VPN detection, corporate network detection,
and the VpnToggleContext manager.
"""

from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
    is_vpn_connected,
)


class TestIsVpnConnected:
    """Tests for is_vpn_connected function."""

    @patch("subprocess.run")
    def test_returns_true_when_adapter_found(self, mock_run):
        """Test returns True when Junos/Pulse adapter is up."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1"  # One adapter found
        mock_run.return_value = mock_result

        result = is_vpn_connected()

        assert result is True

    @patch("subprocess.run")
    def test_returns_false_when_no_adapter(self, mock_run):
        """Test returns False when no VPN adapter found."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0"  # No adapters found
        mock_run.return_value = mock_result

        result = is_vpn_connected()

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_on_powershell_error(self, mock_run):
        """Test returns False when PowerShell command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        result = is_vpn_connected()

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        """Test returns False when command times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=10)

        result = is_vpn_connected()

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_on_invalid_output(self, mock_run):
        """Test returns False when output is not a valid number."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid"
        mock_run.return_value = mock_result

        result = is_vpn_connected()

        assert result is False
