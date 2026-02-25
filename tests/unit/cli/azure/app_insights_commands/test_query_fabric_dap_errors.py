"""Tests for query_fabric_dap_errors function."""

from agentic_devtools.cli.azure.app_insights_commands import query_fabric_dap_errors


class TestQueryFabricDapErrors:
    """Tests for query_fabric_dap_errors function."""

    def test_function_exists(self):
        """Verify query_fabric_dap_errors is importable and callable."""
        assert callable(query_fabric_dap_errors)
