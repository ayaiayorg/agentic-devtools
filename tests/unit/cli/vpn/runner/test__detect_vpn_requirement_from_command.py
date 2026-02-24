"""Tests for agentic_devtools.cli.vpn.runner._detect_vpn_requirement_from_command."""

from agentic_devtools.cli.vpn.runner import (
    VpnRequirement,
    _detect_vpn_requirement_from_command,
)


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
