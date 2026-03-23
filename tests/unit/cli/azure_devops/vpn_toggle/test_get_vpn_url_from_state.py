"""Tests for get_vpn_url_from_state function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import get_vpn_url_from_state


class TestGetVpnUrlFromState:
    """Tests for get_vpn_url_from_state function."""

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    def test_returns_url_from_state_when_set(self, _mock_config):
        """Should return the VPN URL stored in state."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value="https://vpn.example.com",
        ):
            result = get_vpn_url_from_state()

        assert result == "https://vpn.example.com"

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    def test_returns_none_when_state_not_set(self, _mock_config):
        """Should return None when no VPN URL is configured."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            result = get_vpn_url_from_state()

        assert result is None

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value="https://config.vpn")
    def test_returns_project_config_value(self, _mock_config):
        """Should return VPN URL from project config when available."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            result = get_vpn_url_from_state()

        assert result == "https://config.vpn"

    @patch(
        "agentic_devtools.cli.config.project_config.get_project_config_value",
        return_value="  https://vpn.example.com  ",
    )
    def test_strips_whitespace_from_url(self, _mock_config):
        """Should strip leading/trailing whitespace from VPN URL."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            result = get_vpn_url_from_state()

        assert result == "https://vpn.example.com"

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value="   ")
    def test_returns_none_for_whitespace_only(self, _mock_config):
        """Should return None when URL is whitespace-only."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            result = get_vpn_url_from_state()

        assert result is None
