"""Tests for agentic_devtools.cli.vpn.runner.VpnRequirement."""

from agentic_devtools.cli.vpn.runner import VpnRequirement


class TestVpnRequirement:
    """Tests for VpnRequirement enum."""

    def test_enum_values(self):
        """Test VpnRequirement enum has expected values."""
        assert VpnRequirement.REQUIRE_VPN.value == "require_vpn"
        assert VpnRequirement.REQUIRE_PUBLIC.value == "require_public"
        assert VpnRequirement.SMART.value == "smart"
