"""Tests for agentic_devtools.cli.vpn.runner._detect_vpn_requirement_from_command."""

from unittest.mock import patch

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

    @patch(
        "agentic_devtools.cli.azure_devops.vpn_toggle.get_vpn_hostnames",
        return_value=["jira.example.com", "internal.example.com"],
    )
    def test_vpn_hostname_match(self, _mock_hostnames):
        """Test detection for configured VPN hostnames."""
        result = _detect_vpn_requirement_from_command("curl https://jira.example.com/rest/api/2/issue/PROJ-123")
        assert result == VpnRequirement.REQUIRE_VPN

    @patch(
        "agentic_devtools.cli.azure_devops.vpn_toggle.get_vpn_hostnames",
        return_value=["internal.example.com"],
    )
    def test_internal_hostname_match(self, _mock_hostnames):
        """Test detection for internal hostname."""
        result = _detect_vpn_requirement_from_command("curl https://internal.example.com/api")
        assert result == VpnRequirement.REQUIRE_VPN

    @patch(
        "agentic_devtools.cli.azure_devops.vpn_toggle.get_vpn_hostnames",
        return_value=[],
    )
    def test_no_vpn_hostnames_defaults_to_public(self, _mock_hostnames):
        """Test that commands default to REQUIRE_PUBLIC when no VPN hostnames are configured."""
        result = _detect_vpn_requirement_from_command("curl https://jira.example.com/api")
        assert result == VpnRequirement.REQUIRE_PUBLIC

    def test_unknown_command(self):
        """Test detection for unknown commands defaults to public."""
        result = _detect_vpn_requirement_from_command("echo hello world")
        assert result == VpnRequirement.REQUIRE_PUBLIC
