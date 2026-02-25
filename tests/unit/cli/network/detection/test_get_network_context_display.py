"""Tests for get_network_context_display function."""

from agentic_devtools.cli.network.detection import NetworkContext, get_network_context_display


class TestGetNetworkContextDisplay:
    """Tests for get_network_context_display function."""

    def test_corporate_network_includes_office_emoji(self):
        """Corporate network display should include the office emoji."""
        result = get_network_context_display(NetworkContext.CORPORATE_NETWORK, "In office")

        assert "🏢" in result
        assert "In office" in result

    def test_remote_with_vpn_includes_plug_emoji(self):
        """Remote-with-VPN display should include the plug emoji."""
        result = get_network_context_display(NetworkContext.REMOTE_WITH_VPN, "VPN on")

        assert "🔌" in result
        assert "VPN on" in result

    def test_remote_without_vpn_includes_antenna_emoji(self):
        """Remote-without-VPN display should include the antenna emoji."""
        result = get_network_context_display(NetworkContext.REMOTE_WITHOUT_VPN, "No VPN")

        assert "📡" in result
        assert "No VPN" in result

    def test_unknown_includes_question_emoji(self):
        """Unknown context display should include the question mark emoji."""
        result = get_network_context_display(NetworkContext.UNKNOWN, "Unknown")

        assert "❓" in result
        assert "Unknown" in result

    def test_returns_string(self):
        """Should always return a string."""
        result = get_network_context_display(NetworkContext.CORPORATE_NETWORK, "test")

        assert isinstance(result, str)
