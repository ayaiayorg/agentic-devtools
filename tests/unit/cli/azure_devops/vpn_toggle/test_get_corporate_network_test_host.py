"""Tests for get_corporate_network_test_host function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import get_corporate_network_test_host


class TestGetCorporateNetworkTestHost:
    """Tests for get_corporate_network_test_host function."""

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value="internal.example.com")
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_value_from_config(self, _mock_state, _mock_config):
        """Should return host from project config."""
        result = get_corporate_network_test_host()
        assert result == "internal.example.com"

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value="state.example.com")
    def test_returns_value_from_state(self, _mock_state, _mock_config):
        """Should fall back to state value."""
        result = get_corporate_network_test_host()
        assert result == "state.example.com"

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_none_when_unconfigured(self, _mock_state, _mock_config):
        """Should return None when nothing is configured."""
        result = get_corporate_network_test_host()
        assert result is None
