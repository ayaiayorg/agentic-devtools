"""Tests for query_fabric_dap_errors_async function."""

from agentic_devtools.cli.azure.app_insights_commands import query_fabric_dap_errors_async


class TestQueryFabricDapErrorsAsync:
    """Tests for query_fabric_dap_errors_async function."""

    def test_function_exists(self):
        """Verify query_fabric_dap_errors_async is importable and callable."""
        assert callable(query_fabric_dap_errors_async)
