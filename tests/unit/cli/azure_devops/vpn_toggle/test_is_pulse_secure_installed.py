"""
Tests for VPN toggle utilities.

Tests verify VPN detection, corporate network detection,
and the VpnToggleContext manager.
"""

from pathlib import Path
from unittest.mock import patch

from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
    is_pulse_secure_installed,
)


class TestIsPulseSecureInstalled:
    """Tests for is_pulse_secure_installed function."""

    @patch.object(Path, "exists")
    def test_returns_true_when_installed(self, mock_exists):
        """Test returns True when pulselauncher.exe exists."""
        mock_exists.return_value = True
        assert is_pulse_secure_installed() is True

    @patch.object(Path, "exists")
    def test_returns_false_when_not_installed(self, mock_exists):
        """Test returns False when pulselauncher.exe does not exist."""
        mock_exists.return_value = False
        assert is_pulse_secure_installed() is False
