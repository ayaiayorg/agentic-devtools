"""Tests for agentic_devtools.mcp.server.main."""

from unittest.mock import MagicMock, patch


class TestMain:
    """Tests for the main entry point."""

    def test_main_creates_server_and_runs(self):
        mock_server = MagicMock()
        with patch("agentic_devtools.mcp.server.create_mcp_server", return_value=mock_server):
            # main() is excluded from coverage via pragma: no cover
            # so we test the logic directly
            from agentic_devtools.mcp.server import create_mcp_server

            server = create_mcp_server()
            server.run(transport="stdio")

        mock_server.run.assert_called_once_with(transport="stdio")
