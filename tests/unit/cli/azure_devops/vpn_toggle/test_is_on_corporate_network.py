"""
Tests for VPN toggle utilities.

Tests verify VPN detection, corporate network detection,
and the VpnToggleContext manager.
"""

from unittest.mock import MagicMock, patch

from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
    is_on_corporate_network,
)


class TestIsOnCorporateNetwork:
    """Tests for is_on_corporate_network function."""

    @patch("subprocess.run")
    def test_returns_true_when_corporate_accessible(self, mock_run):
        """Test returns True when internal host returns 'corporate'."""
        mock_result = MagicMock()
        mock_result.stdout = "corporate"
        mock_run.return_value = mock_result

        result = is_on_corporate_network()

        assert result is True

    @patch("subprocess.run")
    def test_returns_false_when_external(self, mock_run):
        """Test returns False when response indicates external (403)."""
        mock_result = MagicMock()
        mock_result.stdout = "external"
        mock_run.return_value = mock_result

        result = is_on_corporate_network()

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_on_timeout(self, mock_run):
        """Test returns False when request times out."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=3)

        result = is_on_corporate_network()

        assert result is False

    @patch("subprocess.run")
    def test_returns_false_on_exception(self, mock_run):
        """Test returns False on general exception."""
        mock_run.side_effect = Exception("Network error")

        result = is_on_corporate_network()

        assert result is False
