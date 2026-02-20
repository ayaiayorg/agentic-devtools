"""
Tests for VPN command runner module.
"""

from unittest.mock import patch

from agentic_devtools.cli.vpn.runner import (
    VpnRequirement,
    _detect_vpn_requirement_from_command,
    run_with_vpn_context,
)


class TestVpnRequirement:
    """Tests for VpnRequirement enum."""

    def test_enum_values(self):
        """Test VpnRequirement enum has expected values."""
        assert VpnRequirement.REQUIRE_VPN.value == "require_vpn"
        assert VpnRequirement.REQUIRE_PUBLIC.value == "require_public"
        assert VpnRequirement.SMART.value == "smart"


class TestDetectVpnRequirementFromCommand:
    """Tests for _detect_vpn_requirement_from_command function."""

    def test_npm_install(self):
        """Test detection for npm install commands."""
        result = _detect_vpn_requirement_from_command("npm install express")
        assert result == VpnRequirement.REQUIRE_PUBLIC

    def test_pip_install(self):
        """Test detection for pip install commands."""
        result = _detect_vpn_requirement_from_command("pip install requests")
        assert result == VpnRequirement.REQUIRE_PUBLIC

    def test_jira_url(self):
        """Test detection for Jira URLs."""
        result = _detect_vpn_requirement_from_command("curl https://jira.swica.ch/rest/api/2/issue/DP-123")
        assert result == VpnRequirement.REQUIRE_VPN

    def test_esb_url(self):
        """Test detection for ESB URLs."""
        result = _detect_vpn_requirement_from_command("curl https://esb.swica.ch/api")
        assert result == VpnRequirement.REQUIRE_VPN

    def test_unknown_command(self):
        """Test detection for unknown commands defaults to public."""
        result = _detect_vpn_requirement_from_command("echo hello world")
        assert result == VpnRequirement.REQUIRE_PUBLIC


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
