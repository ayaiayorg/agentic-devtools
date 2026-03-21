"""Tests for agentic_devtools.mcp.server.main."""

from unittest.mock import MagicMock, patch

from agentic_devtools.mcp.server import main


class TestMain:
    """Tests for the main entry point."""

    def test_main_creates_server_and_runs(self):
        mock_server = MagicMock()
        with patch(
            "agentic_devtools.mcp.server.create_mcp_server",
            return_value=mock_server,
        ) as mock_create:
            main()

        mock_create.assert_called_once_with()
        mock_server.run.assert_called_once_with(transport="stdio")
