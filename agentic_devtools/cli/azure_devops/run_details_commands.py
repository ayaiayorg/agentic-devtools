"""
Azure DevOps pipeline/build run details commands.

Fetch details about a specific pipeline or build run from Azure DevOps.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...state import get_value, is_dry_run
from .auth import get_auth_headers, get_pat
from .config import DEFAULT_ORGANIZATION, DEFAULT_PROJECT
from .helpers import require_requests

# Polling configuration
DEFAULT_POLL_INTERVAL_SECONDS = 30
DEFAULT_MAX_CONSECUTIVE_FAILURES = 3


def _get_temp_folder() -> Path:
    """Get the scripts/temp folder path."""
    # Navigate from agentic_devtools/cli/azure_devops to scripts/temp
    package_dir = Path(__file__).parent.parent.parent.parent
    scripts_dir = package_dir.parent
    temp_dir = scripts_dir / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _save_json(data: Dict[str, Any], run_id: int, source: str) -> Path:
    """
    Save raw JSON response to temp folder.

    Args:
        data: JSON data to save.
        run_id: The run ID.
        source: Source identifier (pipeline, build, pipeline-error, build-error).

    Returns:
        Path to the saved file.
    """
    temp_folder = _get_temp_folder()
    filename = f"temp-wb-patch-run-{run_id}-{source}.json"
    filepath = temp_folder / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return filepath


def _fetch_build_timeline(
    requests_module,
    headers: Dict[str, str],
    organization: str,
    project: str,
    run_id: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch the build timeline to get job/task details.

    Args:
        requests_module: The requests module.
        headers: Auth headers for API calls.
        organization: Azure DevOps organization URL.
        project: Project name.
        run_id: The build ID.

    Returns:
        Tuple of (timeline data or None, error message or None).
    """
    url = f"{organization}/{project}/_apis/build/builds/{run_id}/timeline?api-version=7.0"

    try:
        response = requests_module.get(url, headers=headers)
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Timeline API returned {response.status_code}"
    except Exception as e:
        return None, str(e)


def _fetch_task_log(
    requests_module,
    headers: Dict[str, str],
    log_url: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch log content from a task's log URL.

    Args:
        requests_module: The requests module.
        headers: Auth headers for API calls.
        log_url: The URL to fetch the log from.

    Returns:
        Tuple of (log content or None, error message or None).
    """
    try:
        response = requests_module.get(log_url, headers=headers)
        if response.status_code == 200:
            return response.text, None
        else:
            return None, f"Log API returned {response.status_code}"
    except Exception as e:
        return None, str(e)


def _get_failed_tasks(timeline_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract failed tasks from timeline data.

    Args:
        timeline_data: The timeline response from Azure DevOps.

    Returns:
        List of failed task records with log info.
    """
    records = timeline_data.get("records", [])
    failed_tasks = []

    for record in records:
        # Only get failed Task records (not Stage, Job, Phase)
        if record.get("result") == "failed" and record.get("type") == "Task":
            log_info = record.get("log")
            if log_info and log_info.get("url"):
                failed_tasks.append(
                    {
                        "id": record.get("id"),
                        "name": record.get("name"),
                        "type": record.get("type"),
                        "result": record.get("result"),
                        "log_id": log_info.get("id"),
                        "log_url": log_info.get("url"),
                    }
                )

    return failed_tasks


def _save_log_file(log_content: str, run_id: int, task_name: str) -> Path:
    """
    Save log content to a temp file.

    Args:
        log_content: The log text content.
        run_id: The run ID.
        task_name: Name of the task (sanitized for filename).

    Returns:
        Path to the saved file.
    """
    temp_folder = _get_temp_folder()
    # Sanitize task name for filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_name)
    safe_name = safe_name[:50]  # Limit length
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"temp-run-{run_id}-{safe_name}-{timestamp}.log"
    filepath = temp_folder / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(log_content)

    return filepath


def fetch_failed_job_logs(
    run_id: int,
    organization: str = DEFAULT_ORGANIZATION,
    project: str = DEFAULT_PROJECT,
    vpn_toggle: bool = False,
) -> Dict[str, Any]:
    """
    Fetch and save logs from failed jobs/tasks in a build.

    Args:
        run_id: The build run ID.
        organization: Azure DevOps organization URL.
        project: Project name.
        vpn_toggle: If True, temporarily disconnect VPN while fetching logs.

    Returns:
        Dict with keys: success, failed_tasks, log_files, error
    """
    from .vpn_toggle import (
        NetworkStatus,
        VpnToggleContext,
        check_network_status,
        get_vpn_url_from_state,
    )

    result = {
        "success": False,
        "failed_tasks": [],
        "log_files": [],
        "error": None,
    }

    # Check network status FIRST to avoid slow timeouts and provide clear messaging
    if vpn_toggle:
        network_status, status_msg = check_network_status(verbose=True)
        if network_status == NetworkStatus.CORPORATE_NETWORK_NO_VPN:
            print("  ⚠️  Cannot fetch logs from corporate network (in office without VPN)")
            print("     Log fetching requires external network access.")
            print("     Options: connect via mobile hotspot, or work from home with VPN toggle.")
            result["error"] = "Cannot fetch logs from corporate network (no VPN to toggle)"
            result["success"] = True  # Don't fail the command, just skip log fetching
            return result

    requests = require_requests()
    pat = get_pat()
    headers = get_auth_headers(pat)

    # Fetch timeline (usually works with VPN)
    timeline_data, timeline_error = _fetch_build_timeline(requests, headers, organization, project, run_id)

    if not timeline_data:
        result["error"] = f"Failed to fetch timeline: {timeline_error}"
        return result

    # Get failed tasks
    failed_tasks = _get_failed_tasks(timeline_data)
    result["failed_tasks"] = failed_tasks

    if not failed_tasks:
        result["success"] = True
        return result

    # Fetch and save logs for each failed task
    # Use VPN toggle context if enabled - VPN can sometimes block large log downloads
    vpn_url = get_vpn_url_from_state()
    with VpnToggleContext(auto_toggle=vpn_toggle, vpn_url=vpn_url):
        for task in failed_tasks:
            log_url = task.get("log_url")
            if not log_url:
                continue

            log_content, log_error = _fetch_task_log(requests, headers, log_url)
            if log_content:
                log_path = _save_log_file(log_content, run_id, task["name"])
                result["log_files"].append(
                    {
                        "task_name": task["name"],
                        "path": str(log_path),
                    }
                )

    result["success"] = True
    return result


def _print_failed_logs_summary(log_result: Dict[str, Any], run_id: int) -> None:
    """
    Print a summary of failed task logs.

    Args:
        log_result: Result from fetch_failed_job_logs.
        run_id: The run ID for display.
    """
    if not log_result["success"]:
        print(f"\n⚠️ Could not fetch failure logs: {log_result['error']}")
        return

    failed_tasks = log_result.get("failed_tasks", [])
    log_files = log_result.get("log_files", [])

    if not failed_tasks:
        print("\n📋 No failed tasks found in timeline")
        return

    print(f"\n{'=' * 60}")
    print(f"FAILED TASK LOGS ({len(failed_tasks)} failed task(s))")
    print("=" * 60)

    for task in failed_tasks:
        print(f"\n❌ {task['name']}")

    if log_files:
        print("\n📁 Log files saved to scripts/temp/:")
        for log_file in log_files:
            print(f"   • {log_file['task_name']}")
            print(f"     {log_file['path']}")


def _fetch_pipeline_run(
    requests_module,
    headers: Dict[str, str],
    organization: str,
    project: str,
    run_id: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch run details from the Pipelines API.

    Args:
        requests_module: The requests module.
        headers: Auth headers for API calls.
        organization: Azure DevOps organization URL.
        project: Project name.
        run_id: The run ID to fetch.

    Returns:
        Tuple of (data dict or None, error message or None).
    """
    url = f"{organization}/{project}/_apis/pipelines/runs/{run_id}?api-version=7.0"

    try:
        response = requests_module.get(url, headers=headers)

        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Pipeline API returned {response.status_code}"
    except Exception as e:
        return None, str(e)


def _fetch_build_run(
    requests_module,
    headers: Dict[str, str],
    organization: str,
    project: str,
    run_id: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Fetch run details from the Build API.

    Args:
        requests_module: The requests module.
        headers: Auth headers for API calls.
        organization: Azure DevOps organization URL.
        project: Project name.
        run_id: The build ID to fetch.

    Returns:
        Tuple of (data dict or None, error message or None).
    """
    url = f"{organization}/{project}/_apis/build/builds/{run_id}?api-version=7.0"

    try:
        response = requests_module.get(url, headers=headers)

        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Build API returned {response.status_code}"
    except Exception as e:
        return None, str(e)


def _print_parameters(data: Dict[str, Any], source: str) -> None:
    """
    Print parameters from the run data.

    Args:
        data: The run data dictionary.
        source: The source API (pipeline or build).
    """
    params = None

    if source == "pipeline":
        # Pipeline API uses templateParameters
        params = data.get("templateParameters")
    else:
        # Build API uses parameters (as JSON string)
        params_str = data.get("parameters")
        if params_str:
            try:
                params = json.loads(params_str)
            except json.JSONDecodeError:
                params = {"raw": params_str}

    if params:
        print("\nParameters:")
        for key, value in params.items():
            print(f"  {key}: {value}")
    else:
        print("\nParameters: (none)")


def _print_summary(data: Dict[str, Any], source: str) -> None:
    """
    Print a formatted summary of the run.

    Args:
        data: The run data dictionary.
        source: The source API (pipeline or build).
    """
    print(f"\n{'=' * 60}")
    print(f"Run Details (from {source} API)")
    print(f"{'=' * 60}")

    # Common fields
    print(f"Status       : {data.get('state') or data.get('status', 'N/A')}")
    print(f"Result       : {data.get('result', 'N/A')}")

    # Source branch
    if source == "pipeline":
        resources = data.get("resources", {})
        repos = resources.get("repositories", {})
        self_repo = repos.get("self", {})
        branch = self_repo.get("refName", "N/A")
    else:
        branch = data.get("sourceBranch", "N/A")
    print(f"Source Branch: {branch}")

    # Definition name
    if source == "pipeline":
        pipeline_info = data.get("pipeline", {})
        def_name = pipeline_info.get("name", "N/A")
    else:
        definition = data.get("definition", {})
        def_name = definition.get("name", "N/A")
    print(f"Definition   : {def_name}")

    # Web URL
    links = data.get("_links", {})
    web_link = links.get("web", {})
    web_url = web_link.get("href", "N/A")
    print(f"URL          : {web_url}")

    # Parameters
    _print_parameters(data, source)


def get_run_details_impl(
    run_id: int,
    organization: str = DEFAULT_ORGANIZATION,
    project: str = DEFAULT_PROJECT,
    dry_run: bool = False,
    fetch_logs: bool = False,
    vpn_toggle: bool = False,
) -> Dict[str, Any]:
    """
    Fetch details about a pipeline/build run.

    Tries the pipeline API first, then falls back to the build API.
    The build API typically contains more parameter information.

    Args:
        run_id: The run ID to fetch.
        organization: Azure DevOps organization URL.
        project: Project name.
        dry_run: If True, only print what would be done.
        fetch_logs: If True and run failed, fetch and save logs from failed tasks.
        vpn_toggle: If True and fetching logs, temporarily disconnect VPN.

    Returns:
        Dict with keys: success, source, data, error, saved_path, log_files

    Raises:
        EnvironmentError: If PAT is not set.
    """
    result = {
        "success": False,
        "source": None,
        "data": None,
        "error": None,
        "saved_path": None,
        "log_files": [],
    }

    if dry_run:
        print(f"DRY-RUN: Would fetch run details for ID {run_id}")
        print(f"  Organization: {organization}")
        print(f"  Project     : {project}")
        print(f"  Fetch logs  : {fetch_logs}")
        print(f"  VPN toggle  : {vpn_toggle}")
        print(f"  Endpoints   : /_apis/pipelines/runs/{run_id} (then /_apis/build/builds/{run_id})")
        result["success"] = True
        return result

    requests = require_requests()
    pat = get_pat()
    headers = get_auth_headers(pat)

    # Try pipeline API first
    pipeline_data, pipeline_error = _fetch_pipeline_run(requests, headers, organization, project, run_id)

    if pipeline_data:
        _save_json(pipeline_data, run_id, "pipeline")
    elif pipeline_error:
        _save_json({"error": pipeline_error}, run_id, "pipeline-error")

    # Try build API (preferred for parameters)
    build_data, build_error = _fetch_build_run(requests, headers, organization, project, run_id)

    if build_data:
        saved_path = _save_json(build_data, run_id, "build")
        result["success"] = True
        result["source"] = "build"
        result["data"] = build_data
        result["saved_path"] = str(saved_path)
        _print_summary(build_data, "build")

        # Fetch logs if requested and run failed
        if fetch_logs and build_data.get("result") == "failed":
            log_result = fetch_failed_job_logs(run_id, organization, project, vpn_toggle=vpn_toggle)
            _print_failed_logs_summary(log_result, run_id)
            result["log_files"] = log_result.get("log_files", [])

        return result
    elif build_error:
        _save_json({"error": build_error}, run_id, "build-error")

    # Fall back to pipeline data if build failed
    if pipeline_data:
        saved_path = _save_json(pipeline_data, run_id, "pipeline")
        result["success"] = True
        result["source"] = "pipeline"
        result["data"] = pipeline_data
        result["saved_path"] = str(saved_path)
        _print_summary(pipeline_data, "pipeline")

        # Fetch logs if requested and run failed
        if fetch_logs and pipeline_data.get("result") == "failed":
            log_result = fetch_failed_job_logs(run_id, organization, project, vpn_toggle=vpn_toggle)
            _print_failed_logs_summary(log_result, run_id)
            result["log_files"] = log_result.get("log_files", [])

        return result

    # Both failed
    result["error"] = f"Both APIs failed. Pipeline: {pipeline_error}. Build: {build_error}"
    print(f"Error: {result['error']}", file=sys.stderr)
    return result


def get_run_details() -> None:
    """
    CLI entry point to fetch pipeline/build run details.

    State keys read:
        - run_id: The pipeline/build run ID (required)
        - organization: Azure DevOps organization URL (optional)
        - project: Project name (optional)
        - fetch_logs: If "true", fetch and save logs from failed tasks (optional)
        - vpn_toggle: If "true", temporarily disconnect VPN when fetching logs
        - dry_run: If true, only print what would be done

    CLI args:
        --fetch-logs: Fetch and save logs from failed tasks
        --vpn-toggle: Temporarily disconnect VPN when fetching logs
        --run-id: Override run_id from state

    Output:
        Prints formatted summary and saves raw JSON to scripts/temp/.
        If fetch_logs=true and run failed, also saves task logs.

    Raises:
        SystemExit: On validation or execution errors.
    """
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Fetch pipeline/build run details")
    parser.add_argument(
        "--fetch-logs",
        action="store_true",
        help="Fetch and save logs from failed tasks",
    )
    parser.add_argument(
        "--vpn-toggle",
        action="store_true",
        help="Temporarily disconnect VPN when fetching logs",
    )
    parser.add_argument(
        "--run-id",
        type=int,
        help="Pipeline/build run ID (overrides state)",
    )
    args, _ = parser.parse_known_args()

    dry_run = is_dry_run()

    # Get run_id (CLI arg overrides state)
    if args.run_id:
        run_id = args.run_id
    else:
        run_id_str = get_value("run_id")
        if not run_id_str:
            print(
                "Error: 'run_id' is required. Set it with: dfly-set run_id <run-id> or use --run-id",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            run_id = int(run_id_str)
        except ValueError:
            print(f"Error: 'run_id' must be an integer. Got: '{run_id_str}'", file=sys.stderr)
            sys.exit(1)

    organization = get_value("organization") or DEFAULT_ORGANIZATION
    project = get_value("project") or DEFAULT_PROJECT

    # Get fetch_logs flag (CLI arg overrides state)
    if args.fetch_logs:
        fetch_logs = True
    else:
        fetch_logs_val = get_value("fetch_logs")
        if isinstance(fetch_logs_val, bool):
            fetch_logs = fetch_logs_val
        elif isinstance(fetch_logs_val, str):
            fetch_logs = fetch_logs_val.lower() in ("true", "1", "yes")
        else:
            fetch_logs = False

    # Get vpn_toggle flag (CLI arg overrides state)
    if args.vpn_toggle:
        vpn_toggle = True
    else:
        vpn_toggle_val = get_value("vpn_toggle")
        if isinstance(vpn_toggle_val, bool):
            vpn_toggle = vpn_toggle_val
        elif isinstance(vpn_toggle_val, str):
            vpn_toggle = vpn_toggle_val.lower() in ("true", "1", "yes")
        else:
            vpn_toggle = False

    result = get_run_details_impl(
        run_id=run_id,
        organization=organization,
        project=project,
        dry_run=dry_run,
        fetch_logs=fetch_logs,
        vpn_toggle=vpn_toggle,
    )

    if not result["success"] and not dry_run:
        sys.exit(1)


def _is_run_finished(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Check if a pipeline/build run has finished.

    Args:
        data: The run data from the API.

    Returns:
        Tuple of (is_finished, result_status).
        result_status is None if not finished, otherwise the result string.
    """
    # Build API uses 'status', pipeline API uses 'state'
    status = data.get("status") or data.get("state", "")
    result = data.get("result")

    # Terminal states for build API
    terminal_statuses = {"completed", "cancelling", "cancelled"}

    # Check if finished
    if status.lower() in terminal_statuses:
        return True, result

    # Pipeline API uses 'completed' state
    if status.lower() == "completed":
        return True, result

    return False, None


def wait_for_run_impl(
    run_id: int,
    organization: str = DEFAULT_ORGANIZATION,
    project: str = DEFAULT_PROJECT,
    poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
    max_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    dry_run: bool = False,
    fetch_logs: bool = False,
    vpn_toggle: bool = False,
) -> Dict[str, Any]:
    """
    Poll a pipeline/build run until it completes.

    Args:
        run_id: The run ID to monitor.
        organization: Azure DevOps organization URL.
        project: Project name.
        poll_interval: Seconds between poll attempts.
        max_failures: Max consecutive API failures before giving up.
        dry_run: If True, only print what would be done.
        fetch_logs: If True and run failed, fetch and save logs from failed tasks.
        vpn_toggle: If True and fetching logs, temporarily disconnect VPN.

    Returns:
        Dict with keys: success, finished, result, data, error, poll_count, log_files
    """
    result = {
        "success": False,
        "finished": False,
        "result": None,
        "data": None,
        "error": None,
        "poll_count": 0,
        "log_files": [],
    }

    if dry_run:
        print(f"DRY-RUN: Would poll run {run_id} until completion")
        print(f"  Poll interval: {poll_interval}s")
        print(f"  Max consecutive failures: {max_failures}")
        print(f"  Fetch logs on failure: {fetch_logs}")
        print(f"  VPN toggle: {vpn_toggle}")
        result["success"] = True
        return result

    consecutive_failures = 0
    poll_count = 0

    print(f"Waiting for pipeline run {run_id} to complete...")
    print(f"Poll interval: {poll_interval}s, max consecutive failures: {max_failures}")
    print("-" * 60)

    while True:
        poll_count += 1
        result["poll_count"] = poll_count

        # Fetch run details
        details = get_run_details_impl(
            run_id=run_id,
            organization=organization,
            project=project,
            dry_run=False,
        )

        if not details["success"]:
            consecutive_failures += 1
            print(f"\n[Poll {poll_count}] Failed to fetch run details ({consecutive_failures}/{max_failures})")

            if consecutive_failures >= max_failures:
                result["error"] = f"Failed to fetch run details {max_failures} times consecutively"
                print(f"\nError: {result['error']}", file=sys.stderr)
                return result

            print(f"Retrying in {poll_interval}s...")
            time.sleep(poll_interval)
            continue

        # Reset failure counter on success
        consecutive_failures = 0
        data = details["data"]
        result["data"] = data

        # Check if finished
        is_finished, run_result = _is_run_finished(data)

        if is_finished:
            result["success"] = True
            result["finished"] = True
            result["result"] = run_result

            print("\n" + "=" * 60)
            print("PIPELINE RUN COMPLETED")
            print("=" * 60)
            print(f"Run ID    : {run_id}")
            print(f"Result    : {run_result or 'unknown'}")
            print(f"Poll Count: {poll_count}")

            # Get URL from data
            links = data.get("_links", {})
            web_link = links.get("web", {})
            web_url = web_link.get("href", "N/A")
            print(f"URL       : {web_url}")

            # Print result-specific message
            if run_result and run_result.lower() == "succeeded":
                print("\n✅ Pipeline run SUCCEEDED")
            elif run_result and run_result.lower() == "failed":
                print("\n❌ Pipeline run FAILED")
                # Fetch logs if requested
                if fetch_logs:
                    log_result = fetch_failed_job_logs(run_id, organization, project, vpn_toggle=vpn_toggle)
                    _print_failed_logs_summary(log_result, run_id)
                    result["log_files"] = log_result.get("log_files", [])
            elif run_result and run_result.lower() == "canceled":
                print("\n⚠️ Pipeline run was CANCELED")
            else:
                print(f"\n⚠️ Pipeline run finished with result: {run_result}")

            return result

        # Still running - report status and wait
        status = data.get("status") or data.get("state", "unknown")
        print(f"[Poll {poll_count}] Status: {status} - waiting {poll_interval}s...")
        time.sleep(poll_interval)


def wait_for_run() -> None:
    """
    CLI entry point to wait for a pipeline/build run to complete.

    Polls the run status at regular intervals until it finishes.
    Succeeds when the run completes (regardless of run result).
    Fails only if unable to fetch run details repeatedly.

    State keys read:
        - run_id: The pipeline/build run ID (required)
        - organization: Azure DevOps organization URL (optional)
        - project: Project name (optional)
        - poll_interval: Seconds between polls (optional, default 30)
        - max_failures: Max consecutive fetch failures (optional, default 3)
        - fetch_logs: If "true", fetch and save logs from failed tasks (optional)
        - vpn_toggle: If "true", temporarily disconnect VPN when fetching logs
        - dry_run: If true, only print what would be done

    CLI args:
        --fetch-logs: Fetch and save logs from failed tasks
        --vpn-toggle: Temporarily disconnect VPN when fetching logs
        --run-id: Override run_id from state
        --poll-interval: Override poll interval from state

    Output:
        Prints status updates during polling and final result summary.
        If fetch_logs=true and run failed, also saves task logs.

    Raises:
        SystemExit: On validation errors or repeated fetch failures.
    """
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Wait for a pipeline/build run to complete")
    parser.add_argument(
        "--fetch-logs",
        action="store_true",
        help="Fetch and save logs from failed tasks",
    )
    parser.add_argument(
        "--vpn-toggle",
        action="store_true",
        help="Temporarily disconnect VPN when fetching logs",
    )
    parser.add_argument(
        "--run-id",
        type=int,
        help="Pipeline/build run ID (overrides state)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        help="Seconds between polls (overrides state)",
    )
    args, _ = parser.parse_known_args()

    dry_run = is_dry_run()

    # Get run_id (CLI arg overrides state)
    if args.run_id:
        run_id = args.run_id
    else:
        run_id_str = get_value("run_id")
        if not run_id_str:
            print(
                "Error: 'run_id' is required. Set it with: dfly-set run_id <run-id> or use --run-id",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            run_id = int(run_id_str)
        except ValueError:
            print(
                f"Error: 'run_id' must be an integer. Got: '{run_id_str}'",
                file=sys.stderr,
            )
            sys.exit(1)

    organization = get_value("organization") or DEFAULT_ORGANIZATION
    project = get_value("project") or DEFAULT_PROJECT

    # Get poll_interval (CLI arg overrides state)
    if args.poll_interval:
        poll_interval = args.poll_interval
    else:
        poll_interval_str = get_value("poll_interval")
        poll_interval = DEFAULT_POLL_INTERVAL_SECONDS
        if poll_interval_str:
            try:
                poll_interval = int(poll_interval_str)
            except ValueError:
                print(
                    f"Warning: Invalid poll_interval '{poll_interval_str}', "
                    f"using default {DEFAULT_POLL_INTERVAL_SECONDS}s"
                )

    max_failures_str = get_value("max_failures")
    max_failures = DEFAULT_MAX_CONSECUTIVE_FAILURES
    if max_failures_str:
        try:
            max_failures = int(max_failures_str)
        except ValueError:
            print(
                f"Warning: Invalid max_failures '{max_failures_str}', using default {DEFAULT_MAX_CONSECUTIVE_FAILURES}"
            )

    # Get fetch_logs flag (CLI arg overrides state)
    if args.fetch_logs:
        fetch_logs = True
    else:
        fetch_logs_val = get_value("fetch_logs")
        if isinstance(fetch_logs_val, bool):
            fetch_logs = fetch_logs_val
        elif isinstance(fetch_logs_val, str):
            fetch_logs = fetch_logs_val.lower() in ("true", "1", "yes")
        else:
            fetch_logs = False

    # Get vpn_toggle flag (CLI arg overrides state)
    if args.vpn_toggle:
        vpn_toggle = True
    else:
        vpn_toggle_val = get_value("vpn_toggle")
        if isinstance(vpn_toggle_val, bool):
            vpn_toggle = vpn_toggle_val
        elif isinstance(vpn_toggle_val, str):
            vpn_toggle = vpn_toggle_val.lower() in ("true", "1", "yes")
        else:
            vpn_toggle = False

    result = wait_for_run_impl(
        run_id=run_id,
        organization=organization,
        project=project,
        poll_interval=poll_interval,
        max_failures=max_failures,
        dry_run=dry_run,
        fetch_logs=fetch_logs,
        vpn_toggle=vpn_toggle,
    )

    if not result["success"] and not dry_run:
        sys.exit(1)
