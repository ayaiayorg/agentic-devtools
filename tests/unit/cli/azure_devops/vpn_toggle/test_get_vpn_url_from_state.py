"""Tests for get_vpn_url_from_state function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import get_vpn_url_from_state


class TestGetVpnUrlFromState:
    """Tests for get_vpn_url_from_state function."""

    def test_returns_url_from_state_when_set(self):
        """Should return the VPN URL stored in state."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value="https://vpn.example.com",
        ):
            result = get_vpn_url_from_state()

        assert result == "https://vpn.example.com"

    def test_returns_default_url_when_state_not_set(self):
        """Should return the default VPN URL when none is set in state."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            result = get_vpn_url_from_state()

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self):
        """Return value should always be a string."""
        with patch(
            "agentic_devtools.state.get_value",
            return_value=None,
        ):
            result = get_vpn_url_from_state()

        assert isinstance(result, str)
