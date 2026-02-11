"""
Azure CLI utilities package.

This package provides command-line tools for interacting with Azure services
directly via the Azure CLI, including Application Insights queries.

Commands:
    - agdt-query-app-insights: Query Application Insights with KQL
    - agdt-query-fabric-dap-errors: Query Fabric DAP error logs
    - agdt-query-fabric-dap-provisioning: Query Fabric DAP provisioning flow logs
    - agdt-query-fabric-dap-timeline: Query Fabric DAP provisioning timeline
"""

from .app_insights_commands import (
    query_app_insights,
    query_app_insights_async,
    query_fabric_dap_errors,
    query_fabric_dap_errors_async,
    query_fabric_dap_provisioning,
    query_fabric_dap_provisioning_async,
    query_fabric_dap_timeline,
    query_fabric_dap_timeline_async,
)
from .auth import (
    ensure_azure_account,
    get_current_azure_account,
    switch_azure_account,
)
from .config import (
    APP_INSIGHTS_CONFIG,
    AzureAccount,
    get_account_for_environment,
)

__all__ = [
    # Commands
    "query_app_insights",
    "query_app_insights_async",
    "query_fabric_dap_errors",
    "query_fabric_dap_errors_async",
    "query_fabric_dap_provisioning",
    "query_fabric_dap_provisioning_async",
    "query_fabric_dap_timeline",
    "query_fabric_dap_timeline_async",
    # Auth
    "ensure_azure_account",
    "get_current_azure_account",
    "switch_azure_account",
    # Config
    "APP_INSIGHTS_CONFIG",
    "AzureAccount",
    "get_account_for_environment",
]
