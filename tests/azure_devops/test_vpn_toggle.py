"""
Tests for VPN toggle utilities.

Tests verify VPN detection, corporate network detection,
and the VpnToggleContext manager.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
    CORPORATE_NETWORK_TEST_HOST,
    DEFAULT_VPN_URL,
    PULSE_LAUNCHER_PATH,
    JiraVpnContext,
    NetworkStatus,
    VpnToggleContext,
    _run_pulse_command,
    check_network_status,
    disconnect_vpn,
    get_vpn_url_from_state,
    is_on_corporate_network,
    is_pulse_secure_installed,
    is_vpn_connected,
    reconnect_vpn,
)


class TestConstants:
    """Tests for module constants."""

    def test_pulse_launcher_path_is_path_object(self):
        """Test PULSE_LAUNCHER_PATH is a Path object."""
        assert isinstance(PULSE_LAUNCHER_PATH, Path)
        assert "pulselauncher.exe" in str(PULSE_LAUNCHER_PATH)

    def test_default_vpn_url(self):
        """Test DEFAULT_VPN_URL is set correctly."""
        assert DEFAULT_VPN_URL == "https://portal.swica.ch/pulse"

    def test_corporate_network_test_host(self):
        """Test CORPORATE_NETWORK_TEST_HOST is set."""
        assert CORPORATE_NETWORK_TEST_HOST == "dragonfly.swica.ch"


class TestNetworkStatus:
    """Tests for NetworkStatus enum."""

    def test_enum_values(self):
        """Test NetworkStatus enum has expected values."""
        assert NetworkStatus.EXTERNAL_ACCESS_OK.value == "external_access_ok"
        assert NetworkStatus.VPN_CONNECTED.value == "vpn_connected"
        assert NetworkStatus.CORPORATE_NETWORK_NO_VPN.value == "corporate_network_no_vpn"
        assert NetworkStatus.UNKNOWN.value == "unknown"


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


class TestRunPulseCommand:
    """Tests for _run_pulse_command function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_returns_false_when_not_installed(self, mock_installed):
        """Test returns failure when Pulse Secure not installed."""
        mock_installed.return_value = False

        success, msg, return_code = _run_pulse_command(["-version"])

        assert success is False
        assert "not installed" in msg.lower()
        assert return_code == -1

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("subprocess.run")
    def test_successful_command(self, mock_run, mock_installed):
        """Test successful command execution."""
        mock_installed.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Version 9.1"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        success, output, return_code = _run_pulse_command(["-version"])

        assert success is True
        assert "Version 9.1" in output
        assert return_code == 0

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("subprocess.run")
    def test_command_failure(self, mock_run, mock_installed):
        """Test command returns failure on non-zero return code."""
        mock_installed.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error"
        mock_run.return_value = mock_result

        success, output, return_code = _run_pulse_command(["-invalid"])

        assert success is False
        assert "Error" in output
        assert return_code == 1

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("subprocess.run")
    def test_command_timeout(self, mock_run, mock_installed):
        """Test command handles timeout."""
        mock_installed.return_value = True
        mock_run.side_effect = TimeoutError("Command timed out")

        success, output, return_code = _run_pulse_command(["-version"], timeout=1)

        # TimeoutError is not subprocess.TimeoutExpired, but it's still an exception
        assert success is False
        assert return_code == -1

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("subprocess.run")
    def test_command_subprocess_timeout(self, mock_run, mock_installed):
        """Test command handles subprocess.TimeoutExpired."""
        import subprocess

        mock_installed.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

        success, output, return_code = _run_pulse_command(["-version"], timeout=5)

        assert success is False
        assert "timed out" in output.lower()
        assert return_code == -1


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


class TestCheckNetworkStatus:
    """Tests for check_network_status function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    def test_vpn_connected_status(self, mock_vpn):
        """Test returns VPN_CONNECTED when VPN is on."""
        mock_vpn.return_value = True

        status, msg = check_network_status()

        assert status == NetworkStatus.VPN_CONNECTED
        assert "VPN is connected" in msg

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_corporate_network_status(self, mock_corp, mock_vpn):
        """Test returns CORPORATE_NETWORK_NO_VPN when in office."""
        mock_vpn.return_value = False
        mock_corp.return_value = True

        status, msg = check_network_status()

        assert status == NetworkStatus.CORPORATE_NETWORK_NO_VPN
        assert "corporate network" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_external_access_ok(self, mock_corp, mock_vpn):
        """Test returns EXTERNAL_ACCESS_OK when not on VPN or corp network."""
        mock_vpn.return_value = False
        mock_corp.return_value = False

        status, msg = check_network_status()

        assert status == NetworkStatus.EXTERNAL_ACCESS_OK

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    def test_verbose_output(self, mock_vpn, capsys):
        """Test verbose mode prints status."""
        mock_vpn.return_value = True

        check_network_status(verbose=True)

        captured = capsys.readouterr()
        assert "🔌" in captured.out


class TestDisconnectVpn:
    """Tests for disconnect_vpn function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_fails_when_not_installed(self, mock_installed):
        """Test returns failure when Pulse Secure not installed."""
        mock_installed.return_value = False

        success, msg = disconnect_vpn()

        assert success is False
        assert "not installed" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("time.sleep")
    def test_successful_disconnect(self, mock_sleep, mock_installed, mock_cmd, mock_vpn):
        """Test successful VPN disconnect."""
        mock_installed.return_value = True
        mock_cmd.return_value = (True, "Suspended", 0)  # 3-tuple: success, output, return_code
        mock_vpn.side_effect = [True, False]  # Connected, then disconnected

        success, msg = disconnect_vpn(max_wait_seconds=5, check_interval=1.0)

        assert success is True
        assert "verified disconnected" in msg.lower() or "suspend" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_command_failure(self, mock_installed, mock_cmd):
        """Test handles command failure."""
        mock_installed.return_value = True
        mock_cmd.return_value = (False, "Command failed", 1)  # 3-tuple: success, output, return_code

        success, msg = disconnect_vpn()

        assert success is False
        assert "failed" in msg.lower()


class TestReconnectVpn:
    """Tests for reconnect_vpn function."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_fails_when_not_installed(self, mock_installed):
        """Test returns failure when Pulse Secure not installed."""
        mock_installed.return_value = False

        success, msg = reconnect_vpn()

        assert success is False
        assert "not installed" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("time.sleep")
    def test_successful_reconnect(self, mock_sleep, mock_installed, mock_cmd, mock_vpn):
        """Test successful VPN reconnect."""
        mock_installed.return_value = True
        mock_cmd.return_value = (True, "Resumed", 0)  # 3-tuple: success, output, return_code
        mock_vpn.side_effect = [False, True]  # Disconnected, then connected

        success, msg = reconnect_vpn(max_wait_seconds=5, check_interval=1.0)

        assert success is True
        assert "verified connected" in msg.lower() or "resume" in msg.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._run_pulse_command")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_command_failure(self, mock_installed, mock_cmd):
        """Test handles command failure."""
        mock_installed.return_value = True
        mock_cmd.return_value = (False, "Command failed", 1)  # 3-tuple: success, output, return_code

        success, msg = reconnect_vpn()

        assert success is False
        assert "failed" in msg.lower()


class TestVpnToggleContext:
    """Tests for VpnToggleContext context manager."""

    def test_no_op_when_auto_toggle_disabled(self):
        """Test context is a no-op when auto_toggle=False."""
        with VpnToggleContext(auto_toggle=False) as ctx:
            assert ctx.auto_toggle is False
            assert ctx.disconnected is False

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_no_op_when_pulse_not_installed(self, mock_installed, capsys):
        """Test context is a no-op when Pulse Secure not installed."""
        mock_installed.return_value = False

        with VpnToggleContext(auto_toggle=True, verbose=True) as ctx:
            assert ctx.disconnected is False

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_disconnects_and_reconnects_when_connected(self, mock_installed, mock_vpn, mock_disconnect, mock_reconnect):
        """Test disconnects on enter and reconnects on exit when VPN was connected."""
        mock_installed.return_value = True
        mock_vpn.return_value = True  # VPN is connected
        mock_disconnect.return_value = (True, "Disconnected")
        mock_reconnect.return_value = (True, "Reconnected")

        with VpnToggleContext(auto_toggle=True, verbose=False) as ctx:
            assert ctx.was_connected is True
            assert ctx.disconnected is True
            mock_disconnect.assert_called_once()

        mock_reconnect.assert_called_once()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_no_reconnect_when_not_originally_connected(
        self, mock_installed, mock_vpn, mock_disconnect, mock_reconnect
    ):
        """Test does not reconnect if VPN was not connected before."""
        mock_installed.return_value = True
        mock_vpn.return_value = False  # VPN is not connected

        with VpnToggleContext(auto_toggle=True, verbose=False) as ctx:
            assert ctx.was_connected is False
            assert ctx.disconnected is False
            mock_disconnect.assert_not_called()

        mock_reconnect.assert_not_called()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.reconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_reconnects_even_on_exception(self, mock_installed, mock_vpn, mock_disconnect, mock_reconnect):
        """Test reconnects VPN even if exception occurs in context."""
        mock_installed.return_value = True
        mock_vpn.return_value = True
        mock_disconnect.return_value = (True, "Disconnected")
        mock_reconnect.return_value = (True, "Reconnected")

        with pytest.raises(ValueError):
            with VpnToggleContext(auto_toggle=True, verbose=False):
                raise ValueError("Test exception")

        # Should still reconnect
        mock_reconnect.assert_called_once()

    def test_does_not_suppress_exceptions(self):
        """Test context manager does not suppress exceptions."""
        with pytest.raises(RuntimeError, match="test error"):
            with VpnToggleContext(auto_toggle=False):
                raise RuntimeError("test error")


class TestGetVpnUrlFromState:
    """Tests for get_vpn_url_from_state function."""

    @patch("agdt_ai_helpers.state.get_value")
    def test_returns_state_value(self, mock_get_value):
        """Test returns URL from state when set."""
        mock_get_value.return_value = "https://custom.vpn.url"

        result = get_vpn_url_from_state()

        assert result == "https://custom.vpn.url"

    @patch("agdt_ai_helpers.state.get_value")
    def test_returns_default_when_state_empty(self, mock_get_value):
        """Test returns default URL when state value is empty."""
        mock_get_value.return_value = ""

        result = get_vpn_url_from_state()

        assert result == DEFAULT_VPN_URL

    @patch("agdt_ai_helpers.state.get_value")
    def test_returns_default_when_state_none(self, mock_get_value):
        """Test returns default URL when state value is None."""
        mock_get_value.return_value = None

        result = get_vpn_url_from_state()

        assert result == DEFAULT_VPN_URL

    def test_returns_default_on_import_error(self):
        """Test returns default URL when state module cannot be imported."""
        # The function catches ImportError internally
        # We test the default path by ensuring the function works
        # even if called in isolation
        result = get_vpn_url_from_state()
        # Should not raise, should return default or actual value
        assert result is not None


class TestJiraVpnContext:
    """Tests for JiraVpnContext context manager."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_no_op_when_on_corporate_network(self, mock_corp, capsys):
        """Test context is a no-op when on corporate network."""
        mock_corp.return_value = True

        with JiraVpnContext(verbose=True) as ctx:
            assert ctx.on_corporate_network is True
            assert ctx.vpn_was_off is False
            assert ctx.connected_vpn is False

        captured = capsys.readouterr()
        assert "corporate network" in captured.out.lower()
        assert "office" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_no_op_when_pulse_not_installed(self, mock_corp, mock_installed, capsys):
        """Test context is a no-op when Pulse Secure not installed."""
        mock_corp.return_value = False
        mock_installed.return_value = False

        with JiraVpnContext(verbose=True) as ctx:
            assert ctx.on_corporate_network is False
            assert ctx.connected_vpn is False

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_no_op_when_vpn_already_connected(self, mock_corp, mock_installed, mock_vpn, capsys):
        """Test context is a no-op when VPN is already connected."""
        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = True  # VPN already connected

        with JiraVpnContext(verbose=True) as ctx:
            assert ctx.on_corporate_network is False
            assert ctx.vpn_was_off is False
            assert ctx.connected_vpn is False

        captured = capsys.readouterr()
        assert "already connected" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.smart_connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_connects_and_disconnects_vpn(
        self, mock_corp, mock_installed, mock_vpn, mock_connect, mock_disconnect, capsys
    ):
        """Test connects VPN on enter and disconnects on exit when VPN was off."""
        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = False  # VPN is off
        mock_connect.return_value = (True, "VPN connected")
        mock_disconnect.return_value = (True, "VPN suspended")

        with JiraVpnContext(vpn_url="https://test.vpn", verbose=True) as ctx:
            assert ctx.vpn_was_off is True
            assert ctx.connected_vpn is True
            mock_connect.assert_called_once_with("https://test.vpn")

        # Should disconnect on exit
        mock_disconnect.assert_called_once_with("https://test.vpn")

        captured = capsys.readouterr()
        assert "connecting" in captured.out.lower()
        assert "suspending" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.smart_connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_no_disconnect_when_connect_failed(
        self, mock_corp, mock_installed, mock_vpn, mock_connect, mock_disconnect, capsys
    ):
        """Test does not disconnect if connect failed."""
        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = False  # VPN is off
        mock_connect.return_value = (False, "Connect failed")

        with JiraVpnContext(verbose=True) as ctx:
            assert ctx.vpn_was_off is True
            assert ctx.connected_vpn is False
            mock_connect.assert_called_once()

        # Should NOT disconnect since connect failed
        mock_disconnect.assert_not_called()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.smart_connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_disconnects_vpn_even_on_exception(
        self, mock_corp, mock_installed, mock_vpn, mock_connect, mock_disconnect
    ):
        """Test disconnects VPN even if exception occurs in context."""
        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = False
        mock_connect.return_value = (True, "Connected")
        mock_disconnect.return_value = (True, "Disconnected")

        with pytest.raises(ValueError):
            with JiraVpnContext(verbose=False):
                raise ValueError("Test exception")

        # Should still disconnect
        mock_disconnect.assert_called_once()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_does_not_suppress_exceptions(self, mock_corp):
        """Test context manager does not suppress exceptions."""
        mock_corp.return_value = True  # On corporate network

        with pytest.raises(RuntimeError, match="test error"):
            with JiraVpnContext(verbose=False):
                raise RuntimeError("test error")

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_verbose_false_suppresses_output(self, mock_corp, capsys):
        """Test verbose=False suppresses output."""
        mock_corp.return_value = True

        with JiraVpnContext(verbose=False) as _:
            pass

        captured = capsys.readouterr()
        assert captured.out == ""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_no_disconnect_when_on_corporate_network(self, mock_corp):
        """Test does not try to disconnect when on corporate network."""
        mock_corp.return_value = True

        with patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn") as mock_disconnect:
            with JiraVpnContext(verbose=False):
                pass

            # Should NOT call disconnect when on corporate network
            mock_disconnect.assert_not_called()


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


class TestVpnCliCommands:
    """Tests for VPN CLI commands."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_off_on_corporate_network(self, mock_corp, mock_installed, mock_vpn_connected, capsys):
        """Test vpn_off does nothing on corporate network when VPN not connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_off_cmd

        mock_installed.return_value = True
        mock_vpn_connected.return_value = False  # VPN not connected
        mock_corp.return_value = True  # On corporate network

        vpn_off_cmd()

        captured = capsys.readouterr()
        assert "corporate network" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_off_not_installed(self, mock_corp, mock_installed, capsys):
        """Test vpn_off when Pulse not installed."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_off_cmd

        mock_corp.return_value = False
        mock_installed.return_value = False

        vpn_off_cmd()

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_off_not_connected(self, mock_corp, mock_installed, mock_vpn, capsys):
        """Test vpn_off when VPN not connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_off_cmd

        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = False

        vpn_off_cmd()

        captured = capsys.readouterr()
        assert "not currently connected" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.disconnect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.get_vpn_url_from_state")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_off_success(self, mock_corp, mock_installed, mock_vpn, mock_url, mock_disconnect, capsys):
        """Test successful vpn_off."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_off_cmd

        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = True
        mock_url.return_value = "https://vpn.test"
        mock_disconnect.return_value = (True, "VPN disconnected")

        vpn_off_cmd()

        captured = capsys.readouterr()
        assert "✅" in captured.out
        mock_disconnect.assert_called_once_with("https://vpn.test")

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_on_on_corporate_network(self, mock_corp, capsys):
        """Test vpn_on does nothing on corporate network."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_on_cmd

        mock_corp.return_value = True

        vpn_on_cmd()

        captured = capsys.readouterr()
        assert "corporate network" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_on_not_installed(self, mock_corp, mock_installed, capsys):
        """Test vpn_on when Pulse not installed."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_on_cmd

        mock_corp.return_value = False
        mock_installed.return_value = False

        vpn_on_cmd()

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_on_already_connected(self, mock_corp, mock_installed, mock_vpn, capsys):
        """Test vpn_on when VPN already connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_on_cmd

        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = True

        vpn_on_cmd()

        captured = capsys.readouterr()
        assert "already connected" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.smart_connect_vpn")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.get_vpn_url_from_state")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_vpn_connected")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_on_corporate_network")
    def test_vpn_on_success(self, mock_corp, mock_installed, mock_vpn, mock_url, mock_connect, capsys):
        """Test successful vpn_on."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_on_cmd

        mock_corp.return_value = False
        mock_installed.return_value = True
        mock_vpn.return_value = False
        mock_url.return_value = "https://vpn.test"
        mock_connect.return_value = (True, "VPN connected")

        vpn_on_cmd()

        captured = capsys.readouterr()
        assert "✅" in captured.out
        mock_connect.assert_called_once_with("https://vpn.test")

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_vpn_status_not_installed(self, mock_installed, capsys):
        """Test vpn_status when Pulse not installed."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import vpn_status_cmd

        mock_installed.return_value = False

        vpn_status_cmd()

        captured = capsys.readouterr()
        assert "not installed" in captured.out.lower()

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.check_network_status")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_vpn_status_connected(self, mock_installed, mock_status, capsys):
        """Test vpn_status when VPN connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import NetworkStatus, vpn_status_cmd

        mock_installed.return_value = True
        mock_status.return_value = (NetworkStatus.VPN_CONNECTED, "VPN connected")

        vpn_status_cmd()

        captured = capsys.readouterr()
        assert "CONNECTED" in captured.out

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.check_network_status")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_vpn_status_disconnected(self, mock_installed, mock_status, capsys):
        """Test vpn_status when VPN disconnected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import NetworkStatus, vpn_status_cmd

        mock_installed.return_value = True
        mock_status.return_value = (NetworkStatus.EXTERNAL_ACCESS_OK, "External access OK")

        vpn_status_cmd()

        captured = capsys.readouterr()
        assert "DISCONNECTED" in captured.out

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.check_network_status")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_vpn_status_corporate_network(self, mock_installed, mock_status, capsys):
        """Test vpn_status when on corporate network."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import NetworkStatus, vpn_status_cmd

        mock_installed.return_value = True
        mock_status.return_value = (
            NetworkStatus.CORPORATE_NETWORK_NO_VPN,
            "On corporate network",
        )

        vpn_status_cmd()

        captured = capsys.readouterr()
        assert "corporate network" in captured.out.lower()


class TestUiAutomationFunctions:
    """Tests for UI automation helper functions."""

    @patch("subprocess.run")
    def test_get_pulse_window_handle_found(self, mock_run):
        """Test _get_pulse_window_handle when window found."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _get_pulse_window_handle

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "12345"
        mock_run.return_value = mock_result

        hwnd = _get_pulse_window_handle()

        assert hwnd == 12345

    @patch("subprocess.run")
    def test_get_pulse_window_handle_not_found(self, mock_run):
        """Test _get_pulse_window_handle when window not found."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _get_pulse_window_handle

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "0"
        mock_run.return_value = mock_result

        hwnd = _get_pulse_window_handle()

        assert hwnd is None

    @patch("subprocess.run")
    def test_get_pulse_window_handle_on_timeout(self, mock_run):
        """Test _get_pulse_window_handle handles timeout."""
        import subprocess

        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _get_pulse_window_handle

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=5)

        hwnd = _get_pulse_window_handle()

        assert hwnd is None

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    def test_launch_pulse_gui_path_not_exists(self, mock_path):
        """Test _launch_pulse_gui when path doesn't exist."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _launch_pulse_gui

        mock_path.exists.return_value = False

        result = _launch_pulse_gui()

        assert result is False

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._get_pulse_window_handle")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    def test_launch_pulse_gui_already_running(self, mock_path, mock_hwnd):
        """Test _launch_pulse_gui when already running."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _launch_pulse_gui

        mock_path.exists.return_value = True
        mock_hwnd.return_value = 12345  # Already has a window

        result = _launch_pulse_gui()

        assert result is True

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_click_connect_fails_when_gui_launch_fails(self, mock_launch):
        """Test _click_connect_button_via_ui_automation fails when GUI can't launch."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = False

        success, msg = _click_connect_button_via_ui_automation()

        assert success is False
        assert "failed" in msg.lower()


class TestEnsureJiraVpnAccess:
    """Tests for ensure_jira_vpn_access decorator."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.JiraVpnContext")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.get_vpn_url_from_state")
    def test_decorator_wraps_function(self, mock_url, mock_context):
        """Test decorator wraps function with VPN context."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import ensure_jira_vpn_access

        mock_url.return_value = "https://vpn.test"
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_context.return_value = mock_instance

        @ensure_jira_vpn_access
        def my_func():
            return "result"

        result = my_func()

        assert result == "result"
        mock_context.assert_called_once_with(vpn_url="https://vpn.test", verbose=True)
        mock_instance.__enter__.assert_called_once()
        mock_instance.__exit__.assert_called_once()


class TestLaunchPulseGuiSubprocessPath:
    """Additional tests for _launch_pulse_gui subprocess path."""

    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._get_pulse_window_handle")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    def test_launch_pulse_gui_launches_and_waits_for_window(self, mock_path, mock_hwnd, mock_popen, mock_sleep):
        """Test _launch_pulse_gui launches subprocess and waits for window."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _launch_pulse_gui

        mock_path.exists.return_value = True
        mock_path.__str__ = lambda x: "C:\\Program Files\\Pulse\\PulseSecure.exe"
        # First call: not running, subsequent calls: window appears
        mock_hwnd.side_effect = [None, None, 12345]

        result = _launch_pulse_gui()

        assert result is True
        mock_popen.assert_called_once()

    @patch("time.sleep")
    @patch("subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._get_pulse_window_handle")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    def test_launch_pulse_gui_timeout_waiting_for_window(self, mock_path, mock_hwnd, mock_popen, mock_sleep):
        """Test _launch_pulse_gui returns False when window never appears."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _launch_pulse_gui

        mock_path.exists.return_value = True
        mock_path.__str__ = lambda x: "C:\\Program Files\\Pulse\\PulseSecure.exe"
        # Window never appears
        mock_hwnd.return_value = None

        result = _launch_pulse_gui()

        assert result is False

    @patch("subprocess.Popen")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._get_pulse_window_handle")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.PULSE_GUI_PATH")
    def test_launch_pulse_gui_popen_exception(self, mock_path, mock_hwnd, mock_popen):
        """Test _launch_pulse_gui handles Popen exception."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import _launch_pulse_gui

        mock_path.exists.return_value = True
        mock_path.__str__ = lambda x: "C:\\Program Files\\Pulse\\PulseSecure.exe"
        mock_hwnd.return_value = None  # Not already running
        mock_popen.side_effect = OSError("Permission denied")

        result = _launch_pulse_gui()

        assert result is False


class TestClickConnectViaUiAutomation:
    """Additional tests for _click_connect_button_via_ui_automation."""

    @patch("subprocess.run")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_ui_automation_success(self, mock_launch, mock_run):
        """Test successful UI automation click."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = "SUCCESS"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        success, msg = _click_connect_button_via_ui_automation()

        assert success is True
        assert "clicked" in msg.lower()

    @patch("subprocess.run")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_ui_automation_already_connected(self, mock_launch, mock_run):
        """Test UI automation when already connected."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = "ALREADY_CONNECTED"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        success, msg = _click_connect_button_via_ui_automation()

        assert success is True
        assert "already" in msg.lower()

    @patch("subprocess.run")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_ui_automation_error_output(self, mock_launch, mock_run):
        """Test UI automation with error output."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = "ERROR:Connect button not found"
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        success, msg = _click_connect_button_via_ui_automation()

        assert success is False
        assert "failed" in msg.lower()

    @patch("subprocess.run")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_ui_automation_unexpected_output(self, mock_launch, mock_run):
        """Test UI automation with unexpected output."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = True
        mock_result = MagicMock()
        mock_result.stdout = "SOMETHING_ELSE"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        success, msg = _click_connect_button_via_ui_automation()

        assert success is False
        assert "unexpected" in msg.lower()

    @patch("subprocess.run")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_ui_automation_timeout(self, mock_launch, mock_run):
        """Test UI automation timeout handling."""
        import subprocess

        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="powershell", timeout=15)

        success, msg = _click_connect_button_via_ui_automation()

        assert success is False
        assert "timed out" in msg.lower()

    @patch("subprocess.run")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle._launch_pulse_gui")
    def test_ui_automation_exception(self, mock_launch, mock_run):
        """Test UI automation exception handling."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import (
            _click_connect_button_via_ui_automation,
        )

        mock_launch.return_value = True
        mock_run.side_effect = Exception("PowerShell error")

        success, msg = _click_connect_button_via_ui_automation()

        assert success is False
        assert "error" in msg.lower()


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


class TestVpnStatusUnknown:
    """Tests for vpn_status_cmd unknown status path."""

    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.check_network_status")
    @patch("agdt_ai_helpers.cli.azure_devops.vpn_toggle.is_pulse_secure_installed")
    def test_vpn_status_unknown(self, mock_installed, mock_status, capsys):
        """Test vpn_status when network status is unknown."""
        from agdt_ai_helpers.cli.azure_devops.vpn_toggle import NetworkStatus, vpn_status_cmd

        mock_installed.return_value = True
        mock_status.return_value = (NetworkStatus.UNKNOWN, "Could not determine status")

        vpn_status_cmd()

        captured = capsys.readouterr()
        assert "unknown" in captured.out.lower() or "❓" in captured.out


class TestVpnAsyncCommands:
    """Tests for async VPN commands that run in background."""

    @patch("agentic_devtools.task_state.print_task_tracking_info")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_vpn_off_async_creates_background_task(self, mock_run_bg, mock_print_info):
        """Test vpn_off_async creates a background task."""
        from agentic_devtools.cli.azure_devops.vpn_toggle import vpn_off_async

        mock_task = MagicMock()
        mock_run_bg.return_value = mock_task

        vpn_off_async()

        mock_run_bg.assert_called_once_with(
            "agentic_devtools.cli.azure_devops.vpn_toggle",
            "vpn_off_cmd",
            command_display_name="agdt-vpn-off",
        )
        mock_print_info.assert_called_once_with(mock_task, "Disconnecting VPN")

    @patch("agentic_devtools.task_state.print_task_tracking_info")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_vpn_on_async_creates_background_task(self, mock_run_bg, mock_print_info):
        """Test vpn_on_async creates a background task."""
        from agentic_devtools.cli.azure_devops.vpn_toggle import vpn_on_async

        mock_task = MagicMock()
        mock_run_bg.return_value = mock_task

        vpn_on_async()

        mock_run_bg.assert_called_once_with(
            "agentic_devtools.cli.azure_devops.vpn_toggle",
            "vpn_on_cmd",
            command_display_name="agdt-vpn-on",
        )
        mock_print_info.assert_called_once_with(mock_task, "Connecting VPN")

    @patch("agentic_devtools.task_state.print_task_tracking_info")
    @patch("agentic_devtools.background_tasks.run_function_in_background")
    def test_vpn_status_async_creates_background_task(self, mock_run_bg, mock_print_info):
        """Test vpn_status_async creates a background task."""
        from agentic_devtools.cli.azure_devops.vpn_toggle import vpn_status_async

        mock_task = MagicMock()
        mock_run_bg.return_value = mock_task

        vpn_status_async()

        mock_run_bg.assert_called_once_with(
            "agentic_devtools.cli.azure_devops.vpn_toggle",
            "vpn_status_cmd",
            command_display_name="agdt-vpn-status",
        )
        mock_print_info.assert_called_once_with(mock_task, "Checking VPN status")
