"""Tests for agentic_devtools.cli.vpn.runner.run_with_vpn_context."""

import sys
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.network.detection import NetworkContext
from agentic_devtools.cli.vpn.runner import (
    VpnRequirement,
    run_with_vpn_context,
)


def _make_mock_vpn_toggle():
    """Create a reusable mock for the vpn_toggle module."""
    mock_toggle = MagicMock()
    mock_toggle.get_vpn_url_from_state.return_value = "https://mock.vpn"
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_toggle.VpnToggleContext.return_value = mock_ctx
    return mock_toggle


class TestRunWithVpnContext:
    """Tests for run_with_vpn_context function."""

    @patch("agentic_devtools.cli.network.detection.detect_network_context")
    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_import_error(self, mock_execute, mock_detect):
        """Test handling when VPN module not available."""
        mock_detect.side_effect = ImportError("No module")
        mock_execute.return_value = (0, "output", "")

        return_code, stdout, stderr = run_with_vpn_context("echo test")

        assert return_code == 0
        assert stdout == "output"
        mock_execute.assert_called_once()

    @patch("agentic_devtools.cli.network.detection.detect_network_context")
    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_exception_handling(self, mock_execute, mock_detect):
        """Test handling of unexpected exceptions."""
        mock_detect.side_effect = Exception("Unexpected error")
        mock_execute.return_value = (0, "output", "")

        return_code, stdout, stderr = run_with_vpn_context("echo test")

        assert return_code == 0
        mock_execute.assert_called_once()

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_execute_command_success(self, mock_execute):
        """Test successful command execution."""
        mock_execute.return_value = (0, "success", "")

        return_code, stdout, stderr = run_with_vpn_context(
            "echo test",
            requirement=VpnRequirement.REQUIRE_PUBLIC,
        )

        assert return_code == 0
        assert stdout == "success"
        mock_execute.assert_called_once_with("echo test", True)

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_execute_command_failure(self, mock_execute):
        """Test failed command execution."""
        mock_execute.return_value = (1, "", "error")

        return_code, stdout, stderr = run_with_vpn_context(
            "false",
            requirement=VpnRequirement.REQUIRE_PUBLIC,
        )

        assert return_code == 1
        assert stderr == "error"

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_smart_mode_auto_detection(self, mock_execute):
        """Test SMART mode auto-detects requirement from command."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "done", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.REMOTE_WITHOUT_VPN, "remote"),
            ):
                return_code, stdout, _ = run_with_vpn_context(
                    "npm install express",
                    requirement=VpnRequirement.SMART,
                )

        # npm install → REQUIRE_PUBLIC → no VPN needed
        assert return_code == 0
        assert stdout == "done"
        mock_execute.assert_called_once()

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_corporate_network_require_public_message(self, mock_execute):
        """Test CORPORATE_NETWORK with REQUIRE_PUBLIC prints a warning message."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "ok", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.CORPORATE_NETWORK, "office"),
            ):
                return_code, _, _ = run_with_vpn_context(
                    "npm install",
                    requirement=VpnRequirement.REQUIRE_PUBLIC,
                )

        assert return_code == 0
        mock_execute.assert_called_once()

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_corporate_network_require_vpn_message(self, mock_execute):
        """Test CORPORATE_NETWORK with REQUIRE_VPN prints an info message."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "ok", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.CORPORATE_NETWORK, "office"),
            ):
                return_code, _, _ = run_with_vpn_context(
                    "curl https://jira.swica.ch/api",
                    requirement=VpnRequirement.REQUIRE_VPN,
                )

        assert return_code == 0
        mock_execute.assert_called_once()

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_require_vpn_remote_without_vpn_connects(self, mock_execute):
        """Test REQUIRE_VPN on REMOTE_WITHOUT_VPN uses VpnToggleContext to connect."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "result", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.REMOTE_WITHOUT_VPN, "remote no vpn"),
            ):
                return_code, stdout, _ = run_with_vpn_context(
                    "curl https://jira.swica.ch/api",
                    requirement=VpnRequirement.REQUIRE_VPN,
                )

        assert return_code == 0
        assert stdout == "result"
        mock_execute.assert_called_once()
        mock_vpn_toggle.VpnToggleContext.assert_called_once_with(
            vpn_url="https://mock.vpn", ensure_connected=True, verbose=True
        )

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_require_vpn_already_connected_skips_toggle(self, mock_execute):
        """Test REQUIRE_VPN when VPN already active skips VpnToggleContext."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "result", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.REMOTE_WITH_VPN, "remote with vpn"),
            ):
                return_code, _, _ = run_with_vpn_context(
                    "curl https://jira.swica.ch/api",
                    requirement=VpnRequirement.REQUIRE_VPN,
                )

        assert return_code == 0
        mock_execute.assert_called_once()
        mock_vpn_toggle.VpnToggleContext.assert_not_called()

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_require_public_remote_with_vpn_disconnects(self, mock_execute):
        """Test REQUIRE_PUBLIC on REMOTE_WITH_VPN uses VpnToggleContext to disconnect."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "installed", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.REMOTE_WITH_VPN, "remote with vpn"),
            ):
                return_code, stdout, _ = run_with_vpn_context(
                    "npm install lodash",
                    requirement=VpnRequirement.REQUIRE_PUBLIC,
                )

        assert return_code == 0
        assert stdout == "installed"
        mock_execute.assert_called_once()
        mock_vpn_toggle.VpnToggleContext.assert_called_once_with(
            vpn_url="https://mock.vpn", ensure_connected=False, verbose=True
        )

    @patch("agentic_devtools.cli.vpn.runner._execute_command")
    def test_require_public_no_vpn_skips_toggle(self, mock_execute):
        """Test REQUIRE_PUBLIC when not on VPN skips VpnToggleContext."""
        mock_vpn_toggle = _make_mock_vpn_toggle()
        mock_execute.return_value = (0, "installed", "")

        with patch.dict(sys.modules, {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_vpn_toggle}):
            with patch(
                "agentic_devtools.cli.network.detection.detect_network_context",
                return_value=(NetworkContext.REMOTE_WITHOUT_VPN, "remote no vpn"),
            ):
                return_code, _, _ = run_with_vpn_context(
                    "npm install lodash",
                    requirement=VpnRequirement.REQUIRE_PUBLIC,
                )

        assert return_code == 0
        mock_execute.assert_called_once()
        mock_vpn_toggle.VpnToggleContext.assert_not_called()
