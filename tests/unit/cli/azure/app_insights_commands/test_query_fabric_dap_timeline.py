"""Tests for query_fabric_dap_timeline function."""

from agentic_devtools.cli.azure.app_insights_commands import query_fabric_dap_timeline


class TestQueryFabricDapTimeline:
    """Tests for query_fabric_dap_timeline function."""

    def test_function_exists(self):
        """Verify query_fabric_dap_timeline is importable and callable."""
        assert callable(query_fabric_dap_timeline)
