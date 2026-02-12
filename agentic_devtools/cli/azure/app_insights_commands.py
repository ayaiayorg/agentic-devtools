"""Application Insights query commands.

Provides CLI commands for querying Azure Application Insights with KQL,
using the official azure-monitor-query SDK for reliable query execution.

The SDK properly handles large result sets and query filtering, unlike the
az CLI which has issues with query parameter escaping.
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from azure.core.exceptions import HttpResponseError
from azure.identity import AzureCliCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

from ...background_tasks import run_function_in_background
from ...state import get_state_dir, get_value, is_dry_run, set_value
from ...task_state import print_task_tracking_info
from .auth import ensure_azure_account
from .config import (
    get_account_for_environment,
    get_app_insights_config,
)

# Module version for debugging - increment when making changes
MODULE_VERSION = "2.3.0"  # Added -q parameter support to query_app_insights_async


def _get_temp_output_dir() -> Path:
    """Get the temp output directory for query results.

    Uses the state directory (scripts/temp) which is automatically resolved
    relative to the git repo root.
    """
    return get_state_dir()


# Workbench key to cloud_RoleName mapping (for Fabric DAP)
# Format: {workbench_key}: {fabric_dap_role_name_pattern}
WORKBENCH_FABRIC_ROLE_PATTERNS = {
    "STND": "stndfabric",
    "DEVA": "devafabric",
    "DEVB": "devbfabric",
    "DEVC": "devcfabric",
    "DEVD": "devdfabric",
}

# Pre-defined KQL queries for common scenarios
# Note: {combined_filter} is a single WHERE clause with all conditions ANDed together
# for optimal Kusto query execution (avoids multiple WHERE clauses)
FABRIC_DAP_ERROR_QUERY = """
union traces, exceptions
{combined_filter}
| where severityLevel >= 3 or itemType == 'exception'
| project timestamp, severityLevel, cloud_RoleName, operation_Name, message,
    outerMessage, innermostMessage, problemId
| order by timestamp desc
| take {limit}
""".strip()

FABRIC_DAP_PROVISIONING_QUERY = """
union traces, exceptions, requests
{combined_filter}
| project timestamp, severityLevel, cloud_RoleName, operation_Name,
    customDimensions.CategoryName, message, outerMessage, innermostMessage
| order by timestamp asc
| take {limit}
""".strip()

# Timeline query for analyzing dataproduct provisioning duration
FABRIC_DAP_TIMELINE_QUERY = """
union traces, requests
{combined_filter}
| where customDimensions.CategoryName has_any (
    'DataproductProvisioningService', 'DataproductService', 'FabricServiceClient',
    'FabricClientWrapper', 'FabricGateway', 'ContributorGroupCreatedHandler',
    'GroupResolverPollingService', 'WorkspaceProvisionedHandler', 'IntegrationEventHandler',
    'WorkbenchContributorNestingPolling', 'DataproductCommands', 'FabricDataproductCommands')
    or operation_Name has_any ('Provision', 'Create', 'Set', 'Poll', 'HandleAsync')
| project timestamp, severityLevel, cloud_RoleName, operation_Name,
    category = tostring(customDimensions.CategoryName),
    message, duration = toreal(customDimensions.ElapsedMilliseconds)
| order by timestamp asc
| take {limit}
""".strip()


def _build_combined_filter(
    timespan: str,
    dataproduct_id: Optional[str] = None,
    workbench: Optional[str] = None,
    include_mgmt: bool = True,
) -> str:
    """
    Build a single optimized KQL WHERE clause with all conditions ANDed together.

    Combines timestamp, service, and dataproduct filters into one WHERE clause
    for optimal Kusto query execution. This avoids the query engine having to
    scan all data before applying filters (which caused E_QUERY_RESULT_SET_TOO_LARGE errors).

    Args:
        timespan: Time range (e.g., '1h', '30m', '24h').
        dataproduct_id: Optional dataproduct ID or key to filter by.
        workbench: Workbench key (e.g., 'STND') to filter Fabric DAP logs.
        include_mgmt: If True, also include management backend logs.

    Returns:
        Complete WHERE clause like:
        | where timestamp > ago(1h) and (cloud_RoleName has 'stndfabric' or ...)
                and (message contains 'xxx' or tostring(customDimensions) contains 'xxx')
    """
    conditions = [f"timestamp > ago({timespan})"]

    # Build service filter conditions
    service_conditions = []
    if workbench:
        wb_upper = workbench.upper()
        fabric_pattern = WORKBENCH_FABRIC_ROLE_PATTERNS.get(wb_upper)
        if fabric_pattern:
            service_conditions.append(f"cloud_RoleName has '{fabric_pattern}'")
        else:
            service_conditions.append(f"cloud_RoleName has '{wb_upper.lower()}fabric'")
    else:
        service_conditions.append("cloud_RoleName contains 'fabric'")

    if include_mgmt:
        service_conditions.append(
            "cloud_RoleName in ('app-restapi-mgmt-dev-chn-1', 'app-subscriber-mgmt-dev-chn-1', "
            "'app-restapi-mgmt-int-chn-1', 'app-subscriber-mgmt-int-chn-1', "
            "'app-restapi-mgmt-prod-chn-1', 'app-subscriber-mgmt-prod-chn-1')"
        )

    if service_conditions:  # pragma: no branch - defensive: list always has elements
        conditions.append("(" + " or ".join(service_conditions) + ")")

    # Build dataproduct filter condition
    if dataproduct_id:
        conditions.append(
            f"(message contains '{dataproduct_id}' or tostring(customDimensions) contains '{dataproduct_id}')"
        )

    return "| where " + " and ".join(conditions)


def _format_query(
    query_template: str,
    timespan: str = "1h",
    limit: int = 100,
    dataproduct_id: Optional[str] = None,
    workbench: Optional[str] = None,
    include_mgmt: bool = True,
) -> str:
    """Format a query template with combined filter for optimal Kusto execution."""
    combined_filter = _build_combined_filter(
        timespan=timespan,
        dataproduct_id=dataproduct_id,
        workbench=workbench,
        include_mgmt=include_mgmt,
    )
    return query_template.format(
        combined_filter=combined_filter,
        limit=limit,
    )


def _run_app_insights_query(
    environment: str,
    query: str,
    dry_run: bool = False,
    auto_switch_account: bool = True,
    output_file: Optional[Path] = None,
    timeout_seconds: int = 120,
) -> Optional[dict]:
    """
    Run a KQL query against Application Insights using the azure-monitor-query SDK.

    Uses AzureCliCredential to leverage existing 'az login' session, ensuring the
    correct account is active before querying.

    Args:
        environment: Target environment (DEV, INT, PROD).
        query: KQL query string.
        dry_run: If True, only print what would be done.
        auto_switch_account: If True, auto-switch to correct Azure account.
        output_file: If provided, write results to this file instead of returning.
        timeout_seconds: Timeout for the query (default: 120 seconds).

    Returns:
        Query results as dict with 'tables' key, or None on failure.
    """
    config = get_app_insights_config(environment)
    if config is None:
        print(
            f"Error: Unknown environment '{environment}'. Use DEV, INT, or PROD.",
            file=sys.stderr,
        )
        return None

    if dry_run:
        print("DRY-RUN: Would query Application Insights with:")
        print(f"  Environment   : {environment}")
        print(f"  App Insights  : {config.name}")
        print(f"  Resource ID   : {config.resource_id}")
        print(
            f"  Query         : {query[:100]}..."
            if len(query) > 100
            else f"  Query         : {query}"
        )
        if output_file:
            print(f"  Output File   : {output_file}")
        return {"dry_run": True}

    # Ensure correct account is active for AzureCliCredential
    required_account = get_account_for_environment(environment)
    if not ensure_azure_account(required_account, auto_switch=auto_switch_account):
        return None

    print(f"Querying {config.name} in {environment} (timeout: {timeout_seconds}s)...")

    # Debug: Show query being executed (truncated)
    print(
        f"[DEBUG v{MODULE_VERSION}] Query:\n{query[:500]}...\n"
        if len(query) > 500
        else f"[DEBUG v{MODULE_VERSION}] Query:\n{query}\n",
        file=sys.stderr,
    )

    try:
        # Use AzureCliCredential to leverage existing az login session
        credential = AzureCliCredential()
        client = LogsQueryClient(credential)

        # Query the Application Insights resource directly
        # The SDK handles large result sets properly via the REST API
        response = client.query_resource(
            resource_id=config.resource_id,
            query=query,
            timespan=timedelta(days=7),  # Max timespan; actual filtering is in query
            server_timeout=timeout_seconds,
        )

        # Handle partial results (e.g., result truncation)
        if response.status == LogsQueryStatus.PARTIAL:
            print(
                f"Warning: Partial results returned: {response.partial_error}",
                file=sys.stderr,
            )
            tables = response.partial_data
        elif response.status == LogsQueryStatus.SUCCESS:
            tables = response.tables
        else:
            print(f"Error: Query failed with status {response.status}", file=sys.stderr)
            return None

        # Convert to dict format matching the previous CLI output structure
        data = _convert_sdk_response_to_dict(tables)

        if output_file:
            _write_results_to_file(data, output_file)

        return data

    except HttpResponseError as e:
        print(f"Error: HTTP error from Azure Monitor: {e.message}", file=sys.stderr)
        if e.error:
            print(f"  Error code: {e.error.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Failed to query Application Insights: {e}", file=sys.stderr)
        return None


def _convert_sdk_response_to_dict(tables: list) -> dict:
    """
    Convert SDK response tables to dict format matching az CLI output.

    The az CLI returns: {"tables": [{"columns": [...], "rows": [...]}]}
    The SDK returns: list of LogsTable objects with .columns and .rows attributes.
    """
    result_tables = []
    for table in tables:
        # Convert column names to the expected format
        columns = [{"name": col, "type": "string"} for col in table.columns]
        # Convert rows (list of lists)
        rows = [list(row) for row in table.rows]
        result_tables.append({"columns": columns, "rows": rows})

    return {"tables": result_tables}


def _write_results_to_file(data: dict, output_file: Path) -> None:
    """Write query results to a file in readable format."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    tables = data.get("tables", [])
    if not tables:
        output_file.write_text("No results found.\n")
        print(f"Results written to: {output_file}")
        return

    table = tables[0]
    columns = [
        col.get("name", f"col{i}") for i, col in enumerate(table.get("columns", []))
    ]
    rows = table.get("rows", [])

    lines = [
        f"Query Results - {datetime.now().isoformat()}",
        f"Total: {len(rows)} rows",
        "=" * 80,
        "",
    ]

    for i, row in enumerate(rows):
        lines.append(f"--- Result {i + 1} ---")
        for col, val in zip(columns, row):
            if val:
                lines.append(f"  {col}: {val}")
        lines.append("")

    output_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Results written to: {output_file}")


def _print_query_results(data: dict, format_type: str = "table") -> None:
    """Print query results in a readable format."""
    if "dry_run" in data:
        return

    tables = data.get("tables", [])
    if not tables:
        print("No results found.")
        return

    table = tables[0]
    columns = [
        col.get("name", f"col{i}") for i, col in enumerate(table.get("columns", []))
    ]
    rows = table.get("rows", [])

    if not rows:
        print("No results found.")
        return

    print(f"\nFound {len(rows)} results:\n")

    if format_type == "table":
        # Print as table
        print(" | ".join(columns))
        print("-" * (len(" | ".join(columns)) + 10))
        for row in rows:
            print(" | ".join(str(v)[:50] if v else "" for v in row))
    else:
        # Print each row as a block
        for i, row in enumerate(rows):
            print(f"--- Result {i + 1} ---")
            for col, val in zip(columns, row):
                if val:
                    print(f"  {col}: {val}")
            print()


def query_app_insights() -> None:
    """
    Query Application Insights with a custom KQL query.

    State keys read:
        - azure.environment: Target environment - DEV, INT, or PROD (default: DEV)
        - azure.query: KQL query string (required)
        - azure.auto_switch_account: Auto-switch to AZA account (default: true)
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    dry_run = is_dry_run()
    environment = get_value("azure.environment") or "DEV"
    query = get_value("azure.query")
    auto_switch = str(get_value("azure.auto_switch_account") or "true").lower() in (
        "true",
        "1",
        "yes",
    )

    if not query:
        print(
            "Error: 'azure.query' is required. Set it with: agdt-set azure.query '<KQL query>'",
            file=sys.stderr,
        )
        sys.exit(1)

    result = _run_app_insights_query(
        environment=environment,
        query=query,
        dry_run=dry_run,
        auto_switch_account=auto_switch,
    )

    if result is None:
        sys.exit(1)

    _print_query_results(result, format_type="block")


def query_fabric_dap_errors() -> None:
    """
    Query Fabric DAP error logs from Application Insights.

    Runs a pre-defined query for errors (severityLevel >= 3) and exceptions
    from Fabric DAP services.

    State keys read:
        - azure.environment: Target environment - DEV, INT, or PROD (default: DEV)
        - azure.timespan: Time range for query (default: 1h)
        - azure.limit: Maximum results to return (default: 100)
        - azure.dataproduct_id: Filter by dataproduct ID or key (optional)
        - azure.workbench: Workbench key to filter (e.g., STND). If not set, includes all Fabric DAPs.
        - azure.include_mgmt: Include management backend logs (default: true)
        - azure.output_to_file: Write results to temp file instead of console (default: false)
        - azure.auto_switch_account: Auto-switch to AZA account (default: true)
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    dry_run = is_dry_run()
    environment = get_value("azure.environment") or "DEV"
    timespan = get_value("azure.timespan") or "1h"
    limit = int(get_value("azure.limit") or "100")
    dataproduct_id = get_value("azure.dataproduct_id")
    workbench = get_value("azure.workbench")
    include_mgmt = str(get_value("azure.include_mgmt") or "true").lower() in (
        "true",
        "1",
        "yes",
    )
    output_to_file = str(get_value("azure.output_to_file") or "false").lower() in (
        "true",
        "1",
        "yes",
    )
    auto_switch = str(get_value("azure.auto_switch_account") or "true").lower() in (
        "true",
        "1",
        "yes",
    )

    query = _format_query(
        FABRIC_DAP_ERROR_QUERY,
        timespan=timespan,
        limit=limit,
        dataproduct_id=dataproduct_id,
        workbench=workbench,
        include_mgmt=include_mgmt,
    )

    filter_parts = []
    if dataproduct_id:
        filter_parts.append(f"dataproduct='{dataproduct_id}'")
    if workbench:
        filter_parts.append(f"workbench={workbench}")
    filter_msg = f" [{', '.join(filter_parts)}]" if filter_parts else ""
    print(
        f"Querying Fabric DAP errors in {environment} (last {timespan}){filter_msg}..."
    )

    output_file = (
        _get_temp_output_dir() / "temp-fabric-dap-errors.txt"
        if output_to_file
        else None
    )

    result = _run_app_insights_query(
        environment=environment,
        query=query,
        dry_run=dry_run,
        auto_switch_account=auto_switch,
        output_file=output_file,
    )

    if result is None:
        sys.exit(1)

    if not output_to_file:
        _print_query_results(result, format_type="block")


def query_fabric_dap_provisioning() -> None:
    """
    Query Fabric DAP provisioning flow logs from Application Insights.

    Runs a pre-defined query for provisioning-related logs from Fabric DAP
    services, including workspace creation, contributor groups, identities,
    lakehouses, and deployment pipelines.

    State keys read:
        - azure.environment: Target environment - DEV, INT, or PROD (default: DEV)
        - azure.timespan: Time range for query (default: 30m)
        - azure.limit: Maximum results to return (default: 200)
        - azure.dataproduct_id: Filter by dataproduct ID or key (optional)
        - azure.workbench: Workbench key to filter (e.g., STND). If not set, includes all Fabric DAPs.
        - azure.include_mgmt: Include management backend logs (default: true)
        - azure.output_to_file: Write results to temp file instead of console (default: false)
        - azure.background: Run query in background (default: false). Returns task ID immediately.
        - azure.auto_switch_account: Auto-switch to AZA account (default: true)
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    dry_run = is_dry_run()
    background = str(get_value("azure.background") or "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # Background mode: start as detached process and return immediately
    if background and not dry_run:
        task = run_function_in_background(
            "agentic_devtools.cli.azure.app_insights_commands",
            "_query_fabric_dap_provisioning_sync",
            command_display_name="agdt-query-fabric-dap-provisioning",
        )
        print_task_tracking_info(
            task,
            "Running Fabric DAP provisioning query in background (results will be written to file)",
        )
        return

    # Run synchronously
    _query_fabric_dap_provisioning_sync()


def _query_fabric_dap_provisioning_sync() -> int:
    """
    Internal: Run Fabric DAP provisioning query synchronously.

    This is called either directly (non-background mode) or via
    run_function_in_background (background mode).

    Returns:
        Exit code (0 on success, 1 on failure).
    """
    dry_run = is_dry_run()
    environment = get_value("azure.environment") or "DEV"
    timespan = get_value("azure.timespan") or "30m"
    limit = int(get_value("azure.limit") or "200")
    dataproduct_id = get_value("azure.dataproduct_id")
    workbench = get_value("azure.workbench")
    include_mgmt = str(get_value("azure.include_mgmt") or "true").lower() in (
        "true",
        "1",
        "yes",
    )
    # In background mode, always output to file
    output_to_file = str(get_value("azure.output_to_file") or "true").lower() in (
        "true",
        "1",
        "yes",
    )
    auto_switch = str(get_value("azure.auto_switch_account") or "true").lower() in (
        "true",
        "1",
        "yes",
    )

    query = _format_query(
        FABRIC_DAP_PROVISIONING_QUERY,
        timespan=timespan,
        limit=limit,
        dataproduct_id=dataproduct_id,
        workbench=workbench,
        include_mgmt=include_mgmt,
    )

    filter_parts = []
    if dataproduct_id:
        filter_parts.append(f"dataproduct='{dataproduct_id}'")
    if workbench:
        filter_parts.append(f"workbench={workbench}")
    filter_msg = f" [{', '.join(filter_parts)}]" if filter_parts else ""
    print(
        f"Querying Fabric DAP provisioning flow in {environment} (last {timespan}){filter_msg}..."
    )

    output_file = (
        _get_temp_output_dir() / "temp-fabric-dap-provisioning.txt"
        if output_to_file
        else None
    )

    result = _run_app_insights_query(
        environment=environment,
        query=query,
        dry_run=dry_run,
        auto_switch_account=auto_switch,
        output_file=output_file,
    )

    if result is None:
        return 1

    if not output_to_file:
        _print_query_results(result, format_type="block")

    return 0


def query_fabric_dap_timeline() -> None:
    """
    Query Fabric DAP provisioning timeline for performance analysis.

    Runs a timeline query ordered by timestamp (ascending) to analyze
    the duration of each provisioning step for a specific dataproduct.

    State keys read:
        - azure.environment: Target environment - DEV, INT, or PROD (default: DEV)
        - azure.timespan: Time range for query (default: 1h)
        - azure.limit: Maximum results to return (default: 500)
        - azure.dataproduct_id: Filter by dataproduct ID or key (recommended)
        - azure.workbench: Workbench key to filter (e.g., STND). If not set, includes all Fabric DAPs.
        - azure.include_mgmt: Include management backend logs (default: true)
        - azure.output_to_file: Write results to temp file instead of console (default: true)
        - azure.auto_switch_account: Auto-switch to AZA account (default: true)
        - dry_run: If true, only print what would be done

    Raises:
        SystemExit: On validation or execution errors.
    """
    dry_run = is_dry_run()
    environment = get_value("azure.environment") or "DEV"
    timespan = get_value("azure.timespan") or "1h"
    limit = int(get_value("azure.limit") or "500")
    dataproduct_id = get_value("azure.dataproduct_id")
    workbench = get_value("azure.workbench")
    include_mgmt = str(get_value("azure.include_mgmt") or "true").lower() in (
        "true",
        "1",
        "yes",
    )
    # Default to file output for timeline (usually lots of data)
    output_to_file = str(get_value("azure.output_to_file") or "true").lower() in (
        "true",
        "1",
        "yes",
    )
    auto_switch = str(get_value("azure.auto_switch_account") or "true").lower() in (
        "true",
        "1",
        "yes",
    )

    query = _format_query(
        FABRIC_DAP_TIMELINE_QUERY,
        timespan=timespan,
        limit=limit,
        dataproduct_id=dataproduct_id,
        workbench=workbench,
        include_mgmt=include_mgmt,
    )

    filter_parts = []
    if dataproduct_id:
        filter_parts.append(f"dataproduct='{dataproduct_id}'")
    if workbench:
        filter_parts.append(f"workbench={workbench}")
    filter_msg = f" [{', '.join(filter_parts)}]" if filter_parts else ""
    print(
        f"Querying Fabric DAP timeline in {environment} (last {timespan}){filter_msg}..."
    )

    output_file = (
        _get_temp_output_dir() / "temp-fabric-dap-timeline.txt"
        if output_to_file
        else None
    )

    result = _run_app_insights_query(
        environment=environment,
        query=query,
        dry_run=dry_run,
        auto_switch_account=auto_switch,
        output_file=output_file,
    )

    if result is None:
        sys.exit(1)

    if not output_to_file:
        _print_query_results(result, format_type="block")


# Async wrappers for CLI entry points with argparse support


def _set_if_provided(key: str, value: Optional[str]) -> None:
    """Set a state value if provided (not None)."""
    if value is not None:
        set_value(key, value)


def _create_common_parser(description: str) -> argparse.ArgumentParser:
    """Create an argument parser with common options for App Insights queries."""
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["DEV", "INT", "PROD"],
        default=None,
        help="Target environment (default: DEV, or azure.environment state)",
    )
    parser.add_argument(
        "--timespan",
        "-t",
        default=None,
        help="Time range for query, e.g., '1h', '30m', '4h' (default from state or query-specific)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Maximum results to return (default from state or query-specific)",
    )
    parser.add_argument(
        "--dataproduct",
        "-d",
        default=None,
        help="Filter by dataproduct ID or key",
    )
    parser.add_argument(
        "--workbench",
        "-w",
        default=None,
        help="Workbench key to filter (e.g., STND)",
    )
    parser.add_argument(
        "--include-mgmt/--no-include-mgmt",
        dest="include_mgmt",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Include management backend logs (default: true)",
    )
    parser.add_argument(
        "--output-file/--no-output-file",
        dest="output_to_file",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Write results to temp file instead of console",
    )
    parser.add_argument(
        "--auto-switch/--no-auto-switch",
        dest="auto_switch",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Auto-switch to correct Azure account (default: true)",
    )
    return parser


def query_app_insights_async() -> None:
    """
    CLI entry point for running custom KQL queries against Application Insights.

    Supports both CLI arguments and state-based configuration.
    CLI arguments override state values and are saved to state for future calls.

    Examples:
        agdt-query-app-insights -e DEV -q "traces | where message has 'error' | take 10"
        agdt-query-app-insights -t 4h -l 50 -q "exceptions | take 10"
        agdt-query-app-insights  # Uses azure.query from state
    """
    parser = argparse.ArgumentParser(
        description="Query Application Insights with a custom KQL query",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["DEV", "INT", "PROD"],
        default=None,
        help="Target environment (default: DEV, or azure.environment state)",
    )
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        help="Custom KQL query string (required if azure.query not in state)",
    )
    parser.add_argument(
        "--timespan",
        "-t",
        default=None,
        help="Time range for query context, e.g., '1h', '30m', '4h' (informational, filtering is in query)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=None,
        help="Limit hint (informational, use 'take N' in your query)",
    )
    parser.add_argument(
        "--auto-switch/--no-auto-switch",
        dest="auto_switch",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Auto-switch to correct Azure account (default: true)",
    )
    args = parser.parse_args()

    # Set state from CLI args (if provided)
    _set_if_provided("azure.environment", args.environment)
    _set_if_provided("azure.query", args.query)
    _set_if_provided("azure.timespan", args.timespan)
    if args.limit is not None:
        set_value("azure.limit", str(args.limit))
    if args.auto_switch is not None:
        set_value("azure.auto_switch_account", str(args.auto_switch).lower())

    query_app_insights()


def query_fabric_dap_errors_async() -> None:
    """
    CLI entry point for querying Fabric DAP errors with optional arguments.

    Supports both CLI arguments and state-based configuration.
    CLI arguments override state values and are saved to state for future calls.

    Examples:
        agdt-query-fabric-dap-errors -e DEV -t 4h -d ac0ee36e-c6eb-4751-861f-d61400e0f9c3
        agdt-query-fabric-dap-errors --workbench STND --timespan 1h
        agdt-query-fabric-dap-errors  # Uses values from state
    """
    parser = _create_common_parser(
        "Query Fabric DAP error logs from Application Insights"
    )
    args = parser.parse_args()

    # Set state from CLI args (if provided)
    _set_if_provided("azure.environment", args.environment)
    _set_if_provided("azure.timespan", args.timespan)
    if args.limit is not None:
        set_value("azure.limit", str(args.limit))
    _set_if_provided("azure.dataproduct_id", args.dataproduct)
    _set_if_provided("azure.workbench", args.workbench)
    if args.include_mgmt is not None:
        set_value("azure.include_mgmt", str(args.include_mgmt).lower())
    if args.output_to_file is not None:
        set_value("azure.output_to_file", str(args.output_to_file).lower())
    if args.auto_switch is not None:
        set_value("azure.auto_switch_account", str(args.auto_switch).lower())

    query_fabric_dap_errors()


def query_fabric_dap_provisioning_async() -> None:
    """
    CLI entry point for querying Fabric DAP provisioning logs with optional arguments.

    Supports both CLI arguments and state-based configuration.
    CLI arguments override state values and are saved to state for future calls.

    Examples:
        agdt-query-fabric-dap-provisioning -e DEV -t 4h -d ac0ee36e-c6eb-4751-861f-d61400e0f9c3
        agdt-query-fabric-dap-provisioning --workbench STND --output-file
        agdt-query-fabric-dap-provisioning  # Uses values from state
    """
    parser = _create_common_parser(
        "Query Fabric DAP provisioning flow logs from Application Insights"
    )
    parser.add_argument(
        "--background/--no-background",
        dest="background",
        default=None,
        action=argparse.BooleanOptionalAction,
        help="Run query in background (default: false)",
    )
    args = parser.parse_args()

    # Set state from CLI args (if provided)
    _set_if_provided("azure.environment", args.environment)
    _set_if_provided("azure.timespan", args.timespan)
    if args.limit is not None:
        set_value("azure.limit", str(args.limit))
    _set_if_provided("azure.dataproduct_id", args.dataproduct)
    _set_if_provided("azure.workbench", args.workbench)
    if args.include_mgmt is not None:
        set_value("azure.include_mgmt", str(args.include_mgmt).lower())
    if args.output_to_file is not None:
        set_value("azure.output_to_file", str(args.output_to_file).lower())
    if args.auto_switch is not None:
        set_value("azure.auto_switch_account", str(args.auto_switch).lower())
    if args.background is not None:
        set_value("azure.background", str(args.background).lower())

    query_fabric_dap_provisioning()


def query_fabric_dap_timeline_async() -> None:
    """
    CLI entry point for querying Fabric DAP timeline with optional arguments.

    Supports both CLI arguments and state-based configuration.
    CLI arguments override state values and are saved to state for future calls.

    Examples:
        agdt-query-fabric-dap-timeline -e DEV -t 4h -d ac0ee36e-c6eb-4751-861f-d61400e0f9c3
        agdt-query-fabric-dap-timeline --workbench STND --limit 1000
        agdt-query-fabric-dap-timeline  # Uses values from state
    """
    parser = _create_common_parser(
        "Query Fabric DAP provisioning timeline for performance analysis"
    )
    args = parser.parse_args()

    # Set state from CLI args (if provided)
    _set_if_provided("azure.environment", args.environment)
    _set_if_provided("azure.timespan", args.timespan)
    if args.limit is not None:
        set_value("azure.limit", str(args.limit))
    _set_if_provided("azure.dataproduct_id", args.dataproduct)
    _set_if_provided("azure.workbench", args.workbench)
    if args.include_mgmt is not None:
        set_value("azure.include_mgmt", str(args.include_mgmt).lower())
    if args.output_to_file is not None:
        set_value("azure.output_to_file", str(args.output_to_file).lower())
    if args.auto_switch is not None:
        set_value("azure.auto_switch_account", str(args.auto_switch).lower())

    query_fabric_dap_timeline()
