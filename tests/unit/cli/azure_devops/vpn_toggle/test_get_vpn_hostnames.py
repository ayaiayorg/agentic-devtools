"""Tests for get_vpn_hostnames function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.vpn_toggle import get_vpn_hostnames


class TestGetVpnHostnames:
    """Tests for get_vpn_hostnames function."""

    @patch(
        "agentic_devtools.cli.config.project_config.get_project_config_value",
        return_value="jira.example.com,internal.example.com",
    )
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_hostnames_from_config(self, _mock_state, _mock_config):
        """Should return hostnames from project config."""
        result = get_vpn_hostnames()
        assert result == ["jira.example.com", "internal.example.com"]

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value="state.example.com")
    def test_returns_hostnames_from_state(self, _mock_state, _mock_config):
        """Should fall back to state value."""
        result = get_vpn_hostnames()
        assert result == ["state.example.com"]

    @patch("agentic_devtools.cli.config.project_config.get_project_config_value", return_value=None)
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_returns_empty_list_when_unconfigured(self, _mock_state, _mock_config):
        """Should return empty list when nothing is configured."""
        result = get_vpn_hostnames()
        assert result == []

    @patch(
        "agentic_devtools.cli.config.project_config.get_project_config_value", return_value=" host1.com , host2.com "
    )
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_strips_whitespace(self, _mock_state, _mock_config):
        """Should trim whitespace from hostnames."""
        result = get_vpn_hostnames()
        assert result == ["host1.com", "host2.com"]

    @patch(
        "agentic_devtools.cli.config.project_config.get_project_config_value",
        return_value="Jira.Example.COM,INTERNAL.Example.com",
    )
    @patch("agentic_devtools.state.get_value", return_value=None)
    def test_normalizes_to_lowercase(self, _mock_state, _mock_config):
        """Should normalize hostnames to lowercase for case-insensitive matching."""
        result = get_vpn_hostnames()
        assert result == ["jira.example.com", "internal.example.com"]
