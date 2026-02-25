"""Tests for detect_network_context function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.network.detection import NetworkContext, detect_network_context


class TestDetectNetworkContext:
    """Tests for detect_network_context function."""

    def test_returns_remote_with_vpn_when_vpn_connected(self):
        """Should return REMOTE_WITH_VPN when VPN is connected."""
        mock_module = MagicMock()
        mock_module.is_vpn_connected.return_value = True
        mock_module.is_on_corporate_network.return_value = False

        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_module},
        ):
            context, desc = detect_network_context()

        assert context == NetworkContext.REMOTE_WITH_VPN
        assert "VPN" in desc

    def test_returns_corporate_network_when_on_corporate(self):
        """Should return CORPORATE_NETWORK when on the corporate network."""
        mock_module = MagicMock()
        mock_module.is_vpn_connected.return_value = False
        mock_module.is_on_corporate_network.return_value = True

        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_module},
        ):
            context, desc = detect_network_context()

        assert context == NetworkContext.CORPORATE_NETWORK
        assert "corporate" in desc.lower() or "office" in desc.lower()

    def test_returns_remote_without_vpn_when_neither(self):
        """Should return REMOTE_WITHOUT_VPN when not on VPN or corporate network."""
        mock_module = MagicMock()
        mock_module.is_vpn_connected.return_value = False
        mock_module.is_on_corporate_network.return_value = False

        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_module},
        ):
            context, desc = detect_network_context()

        assert context == NetworkContext.REMOTE_WITHOUT_VPN

    def test_returns_unknown_on_general_exception(self):
        """Should return UNKNOWN when an unexpected exception occurs."""
        mock_module = MagicMock()
        mock_module.is_vpn_connected.side_effect = RuntimeError("Unexpected error")

        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_module},
        ):
            context, desc = detect_network_context()

        assert context == NetworkContext.UNKNOWN

    def test_returns_unknown_on_import_error(self):
        """Should return UNKNOWN when vpn_toggle module cannot be imported."""
        mock_module = MagicMock()
        mock_module.is_vpn_connected.side_effect = ImportError("No module")

        with patch.dict(
            "sys.modules",
            {"agentic_devtools.cli.azure_devops.vpn_toggle": mock_module},
        ):
            context, desc = detect_network_context()

        assert isinstance(context, NetworkContext)
        assert isinstance(desc, str)
