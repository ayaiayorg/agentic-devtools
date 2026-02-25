"""Tests for query_fabric_dap_provisioning function."""

from agentic_devtools.cli.azure.app_insights_commands import query_fabric_dap_provisioning


class TestQueryFabricDapProvisioning:
    """Tests for query_fabric_dap_provisioning function."""

    def test_function_exists(self):
        """Verify query_fabric_dap_provisioning is importable and callable."""
        assert callable(query_fabric_dap_provisioning)
