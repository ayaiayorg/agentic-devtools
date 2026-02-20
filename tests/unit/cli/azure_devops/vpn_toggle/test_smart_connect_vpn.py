"""Tests for smart_connect_vpn function."""

from unittest.mock import patch


class TestSmartConnectVpn:
    """Tests for smart_connect_vpn function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_fails_when_not_installed(self, mock_installed):
        """Test returns failure when Pulse Secure not installed."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import smart_connect_vpn

        mock_installed.return_value = False

        success, msg = smart_connect_vpn()

        assert success is False
        assert "not installed" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_already_connected(self, mock_installed, mock_vpn):
        """Test returns success when VPN already connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import smart_connect_vpn

        mock_installed.return_value = True
        mock_vpn.return_value = True

        success, msg = smart_connect_vpn()

        assert success is True
        assert "already" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("time.sleep")
    def test_resumes_suspended_session(self, mock_sleep, mock_installed, mock_cmd, mock_vpn):
        """Test successfully resumes suspended VPN session."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import smart_connect_vpn

        mock_installed.return_value = True
        mock_vpn.side_effect = [False, True]  # First off, then connected
        mock_cmd.return_value = (True, "Resumed", 0)  # Return code 0 = resume accepted

        success, msg = smart_connect_vpn(max_wait_seconds=5, check_interval=1.0)

        assert success is True
        assert "resume" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_full_connect_when_no_suspended_session(self, mock_installed, mock_cmd, mock_vpn, mock_connect):
        """Test calls full connect when return code indicates no suspended session."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import smart_connect_vpn

        mock_installed.return_value = True
        mock_vpn.return_value = False
        mock_cmd.return_value = (False, "No session", 999)  # Return code 999 = no suspended session
        mock_connect.return_value = (True, "Connected via UI")

        success, msg = smart_connect_vpn()

        assert success is True
        mock_connect.assert_called_once()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_full_connect_when_pulse_not_running(self, mock_installed, mock_cmd, mock_vpn, mock_connect):
        """Test calls full connect when Pulse not running (code -1)."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import smart_connect_vpn

        mock_installed.return_value = True
        mock_vpn.return_value = False
        mock_cmd.return_value = (False, "Not running", -1)  # Return code -1 = Pulse not running
        mock_connect.return_value = (True, "Connected")

        success, msg = smart_connect_vpn()

        assert success is True
        mock_connect.assert_called_once()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_fallback_on_unexpected_return_code(self, mock_installed, mock_cmd, mock_vpn, mock_connect):
        """Test falls back to connect_vpn on unexpected return code."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import smart_connect_vpn

        mock_installed.return_value = True
        mock_vpn.return_value = False
        mock_cmd.return_value = (True, "Unexpected", 42)  # Unexpected return code
        mock_connect.return_value = (True, "Connected via fallback")

        success, msg = smart_connect_vpn()

        assert success is True
        mock_connect.assert_called_once()
