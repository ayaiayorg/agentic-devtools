"""Tests for connect_vpn function."""
from unittest.mock import patch


class TestConnectVpn:
    """Tests for connect_vpn function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_fails_when_not_installed(self, mock_installed):
        """Test returns failure when Pulse Secure not installed."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = False

        success, msg = connect_vpn()

        assert success is False
        assert "not installed" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("time.sleep")
    def test_successful_connect_via_ui_automation(self, mock_sleep, mock_installed, mock_ui_auto, mock_vpn):
        """Test successful connect via UI automation."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_ui_auto.return_value = (True, "Connect button clicked")
        mock_vpn.side_effect = [True]  # VPN connects on first check

        success, msg = connect_vpn(max_wait_seconds=5, check_interval=1.0)

        assert success is True
        assert "connected" in msg.lower() or "automation" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("time.sleep")
    def test_connect_already_connected(self, mock_sleep, mock_installed, mock_ui_auto, mock_vpn):
        """Test connect returns success when already connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_ui_auto.return_value = (True, "Already connected")

        success, msg = connect_vpn()

        assert success is True
        assert "already" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_falls_back_to_manual_on_ui_failure(self, mock_installed, mock_ui_auto, mock_gui_path, mock_popen):
        """Test falls back to manual connect when UI automation fails."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_ui_auto.return_value = (False, "UI automation failed")
        mock_gui_path.exists.return_value = False

        success, msg = connect_vpn(max_wait_seconds=1)

        assert success is False
        assert "not found" in msg.lower() or "manually" in msg.lower()

class TestConnectVpnTimeoutPaths:
    """Tests for connect_vpn timeout and manual fallback paths."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_connect_vpn_ui_automation_initiated_but_not_confirmed(
        self, mock_installed, mock_reconnect, mock_ui_click, mock_is_connected
    ):
        """Test connect_vpn when UI automation initiates but connection not confirmed."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_reconnect.return_value = (False, "No suspended session", 999)
        mock_ui_click.return_value = (True, "Connect button clicked")
        # Connection never becomes active during wait period
        mock_is_connected.return_value = False

        success, msg = connect_vpn("https://vpn.test", max_wait_seconds=0.1, check_interval=0.05)

        # Should return True with "initiated" message
        assert success is True
        assert "initiated" in msg.lower()

    @patch("subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_connect_vpn_manual_fallback_success(
        self, mock_installed, mock_reconnect, mock_ui_click, mock_is_connected, mock_path, mock_popen
    ):
        """Test connect_vpn manual fallback path when UI automation fails."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_reconnect.return_value = (False, "No suspended session", 999)
        mock_ui_click.return_value = (False, "UI automation failed")
        mock_path.exists.return_value = True
        # Manual connection succeeds after user connects
        mock_is_connected.side_effect = [False, False, True]

        success, msg = connect_vpn("https://vpn.test", max_wait_seconds=0.2, check_interval=0.05)

        assert success is True
        assert "connected" in msg.lower()

    @patch("subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_connect_vpn_manual_fallback_timeout(
        self, mock_installed, mock_reconnect, mock_ui_click, mock_is_connected, mock_path, mock_popen
    ):
        """Test connect_vpn manual fallback when timeout waiting for user."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_reconnect.return_value = (False, "No suspended session", 999)
        mock_ui_click.return_value = (False, "UI automation failed")
        mock_path.exists.return_value = True
        mock_is_connected.return_value = False  # Never connects

        success, msg = connect_vpn("https://vpn.test", max_wait_seconds=0.1, check_interval=0.05)

        assert success is False
        assert "timed out" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_connect_vpn_gui_not_found(
        self, mock_installed, mock_reconnect, mock_ui_click, mock_is_connected, mock_path
    ):
        """Test connect_vpn when GUI path doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_reconnect.return_value = (False, "No suspended session", 999)
        mock_ui_click.return_value = (False, "UI automation failed")
        mock_path.exists.return_value = False

        success, msg = connect_vpn("https://vpn.test")

        assert success is False
        assert "not found" in msg.lower()

    @patch("subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._click_connect_button_via_ui_automation")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_connect_vpn_popen_fails(
        self, mock_installed, mock_reconnect, mock_ui_click, mock_is_connected, mock_path, mock_popen
    ):
        """Test connect_vpn when Popen fails to launch GUI."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import connect_vpn

        mock_installed.return_value = True
        mock_reconnect.return_value = (False, "No suspended session", 999)
        mock_ui_click.return_value = (False, "UI automation failed")
        mock_path.exists.return_value = True
        mock_popen.side_effect = OSError("Permission denied")

        success, msg = connect_vpn("https://vpn.test")

        assert success is False
        assert "failed to open" in msg.lower()
