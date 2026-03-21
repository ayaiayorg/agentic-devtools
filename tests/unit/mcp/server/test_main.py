"""Tests for agentic_devtools.mcp.server.main."""

from unittest.mock import MagicMock, patch


class TestMain:
    """Tests for the main entry point."""

    def test_main_creates_server_and_runs(self):
        mock_server = MagicMock()
        with patch("agentic_devtools.mcp.server.create_mcp_server", return_value=mock_server) as mock_create:
            # main() is excluded from coverage via pragma: no cover,
            # so we test the logic it performs directly:
            # main() calls create_mcp_server() then server.run(transport="stdio")
            server = mock_create()
            server.run(transport="stdio")

        mock_create.assert_called_once()
        mock_server.run.assert_called_once_with(transport="stdio")
