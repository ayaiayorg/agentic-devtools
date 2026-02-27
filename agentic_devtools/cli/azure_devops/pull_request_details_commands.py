"""
Pull Request Details command - retrieves comprehensive pull request information.

This command fetches pull request metadata, diff information, threads, iterations,
and reviewer state from Azure DevOps.
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional

from ...state import get_pull_request_id, get_state_dir, is_dry_run
from ..git.diff import (
    get_added_lines_info,
    get_diff_entries,
    get_diff_patch,
    normalize_ref_name,
    sync_git_ref,
)
from ..subprocess_utils import run_safe
from .auth import get_auth_headers, get_pat
from .config import AzureDevOpsConfig
from .helpers import verify_az_cli


def _invoke_ado_rest(url: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Make an Azure DevOps REST API GET request."""
    try:
        import requests
    except ImportError:  # pragma: no cover
        print(
            "Error: 'requests' library required. Install with: pip install requests",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Warning: Failed to retrieve data from {url}: {e}", file=sys.stderr)
        return None


def _get_pull_request_threads(
    organization: str,
    project: str,
    repo_id: str,
    pull_request_id: int,
    headers: Dict[str, str],
) -> Optional[List[Dict[str, Any]]]:
    """Fetch pull request comment threads."""
    project_encoded = project.replace(" ", "%20")
    url = (
        f"{organization}/{project_encoded}/_apis/git/repositories/"
        + f"{repo_id}/pullRequests/{pull_request_id}/threads?api-version=7.1-preview.1"
    )
    response = _invoke_ado_rest(url, headers)
    if response and "value" in response:
        return response["value"]
    return None


def _get_pull_request_iterations(
    organization: str,
    project: str,
    repo_id: str,
    pull_request_id: int,
    headers: Dict[str, str],
) -> Optional[List[Dict[str, Any]]]:
    """Fetch pull request iterations."""
    project_encoded = project.replace(" ", "%20")
    url = (
        f"{organization}/{project_encoded}/_apis/git/repositories/"
        + f"{repo_id}/pullRequests/{pull_request_id}/iterations?api-version=7.1-preview.1"
    )
    response = _invoke_ado_rest(url, headers)
    if response and "value" in response:
        return response["value"]
    return None


def _get_iteration_changes(
    organization: str,
    project: str,
    repo_id: str,
    pull_request_id: int,
    iteration_id: int,
    headers: Dict[str, str],
) -> Optional[List[Dict[str, Any]]]:
    """Fetch changes for a specific pull request iteration.

    Args:
        organization: Azure DevOps organization URL
        project: Project name
        repo_id: Repository ID
        pull_request_id: Pull request ID
        iteration_id: Iteration ID to get changes for
        headers: Auth headers

    Returns:
        List of change entries with changeTrackingId, or None if failed
    """
    project_encoded = project.replace(" ", "%20")
    url = (
        f"{organization}/{project_encoded}/_apis/git/repositories/"
        + f"{repo_id}/pullRequests/{pull_request_id}/iterations/{iteration_id}/changes?api-version=7.1-preview.1"
    )
    response = _invoke_ado_rest(url, headers)
    if response and "changeEntries" in response:
        return response["changeEntries"]
    return None


def get_change_tracking_id_for_file(
    organization: str,
    project: str,
    repo_id: str,
    pull_request_id: int,
    iteration_id: int,
    file_path: str,
    headers: Dict[str, str],
) -> Optional[int]:
    """Get the changeTrackingId for a specific file in an iteration.

    Args:
        organization: Azure DevOps organization URL
        project: Project name
        repo_id: Repository ID
        pull_request_id: Pull request ID
        iteration_id: Iteration ID to get changes for
        file_path: Path to the file (with or without leading slash)
        headers: Auth headers

    Returns:
        changeTrackingId for the file, or None if not found
    """
    changes = _get_iteration_changes(organization, project, repo_id, pull_request_id, iteration_id, headers)
    if not changes:
        return None

    # Normalize file path - Azure DevOps uses paths with leading slash
    normalized_path = file_path if file_path.startswith("/") else f"/{file_path}"

    for change in changes:
        item = change.get("item", {})
        change_path = item.get("path", "")
        if change_path == normalized_path:
            return change.get("changeTrackingId")

    return None


def _invoke_ado_rest_post(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Make an Azure DevOps REST API POST request."""
    try:
        import requests
    except ImportError:  # pragma: no cover
        return None

    try:
        post_headers = dict(headers)
        post_headers["Content-Type"] = "application/json"
        response = requests.post(url, headers=post_headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def _get_viewed_files_via_contribution(
    organization: str,
    project_id: Optional[str],
    repo_id: str,
    pull_request_id: int,
    headers: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    Fetch viewed files state via Azure DevOps Contribution API.

    Returns a list of dicts with keys: path, changeTrackingId, objectHash, token
    """
    if not organization or not project_id or not repo_id:
        return []

    payload = {
        "contributionIds": ["ms.vss-code-web.pr-detail-visit-data-provider"],
        "dataProviderContext": {
            "properties": {
                "repositoryId": repo_id,
                "projectId": project_id,
                "pullRequestId": pull_request_id,
            }
        },
    }

    contribution_url = f"{organization}/_apis/Contribution/HierarchyQuery?api-version=7.1-preview.1"
    response = _invoke_ado_rest_post(contribution_url, headers, payload)

    if not response:
        return []

    # Navigate to the viewed state data
    data_providers = response.get("dataProviders", {})
    provider = data_providers.get("ms.vss-code-web.pr-detail-visit-data-provider", {})
    visit = provider.get("visit", {})
    viewed_state_str = visit.get("viewedState")

    if not viewed_state_str:
        return []

    # Parse the viewedState JSON string
    try:
        viewed_state = json.loads(viewed_state_str)
    except (json.JSONDecodeError, TypeError):
        return []

    hashes = viewed_state.get("hashes", {})
    if not hashes:
        return []

    results = []
    for token, _value in hashes.items():
        if not token:  # pragma: no cover
            continue
        # Token format: changeTrackingId@objectHash@path
        segments = token.split("@", 2)
        if len(segments) < 3:
            continue
        path = segments[2]
        if not path:
            continue
        normalized_path = "/" + path.lstrip("/")
        results.append(
            {
                "path": normalized_path,
                "changeTrackingId": segments[0],
                "objectHash": segments[1],
                "token": token,
            }
        )

    return results


def _get_iteration_change_tracking_map(
    organization: str,
    project: str,
    repo_id: str,
    pull_request_id: int,
    iteration_id: Optional[int],
    headers: Dict[str, str],
) -> Dict[str, Dict[str, str]]:
    """
    Get a map of file paths to their change tracking info for a given iteration.

    Returns dict mapping normalized path -> {changeTrackingId, objectId}
    """
    if not organization or not project or not repo_id or not iteration_id:
        return {}

    project_encoded = project.replace(" ", "%20")
    url = (
        f"{organization}/{project_encoded}/_apis/git/repositories/{repo_id}/"
        f"pullRequests/{pull_request_id}/iterations/{iteration_id}/changes"
        f"?api-version=7.1-preview.1&$top=2000"
    )

    response = _invoke_ado_rest(url, headers)
    if not response:
        return {}

    # Extract change entries - try different possible locations in response
    entries = []
    if "value" in response:
        entries = response["value"]
    elif "changeEntries" in response:
        change_entries = response["changeEntries"]
        if isinstance(change_entries, dict) and "value" in change_entries:
            entries = change_entries["value"]
        elif isinstance(change_entries, list):
            entries = change_entries

    result: Dict[str, Dict[str, str]] = {}
    for change in entries:
        if not change:  # pragma: no cover
            continue
        change_tracking_id = change.get("changeTrackingId")
        item = change.get("item", {})
        if not change_tracking_id or not item:
            continue

        path = item.get("path")
        object_id = item.get("objectId")
        if not path:
            continue

        normalized_path = "/" + path.lstrip("/")
        result[normalized_path] = {
            "changeTrackingId": str(change_tracking_id),
            "objectId": object_id or "",
        }

    return result


def _get_current_user_id(organization: str, headers: Dict[str, str]) -> Optional[str]:
    """
    Get the current authenticated user's ID from Azure DevOps.

    Args:
        organization: Azure DevOps organization URL
        headers: Auth headers

    Returns:
        User ID string or None if unable to determine
    """
    url = f"{organization}/_apis/connectionData"
    response = _invoke_ado_rest(url, headers)
    if not response:
        return None
    authenticated_user = response.get("authenticatedUser", {})
    return authenticated_user.get("id")


def _get_reviewer_payload(
    organization: str,
    project: str,
    repo_id: str,
    pull_request_id: int,
    project_id: Optional[str],
    iterations_payload: Optional[List[Dict[str, Any]]],
    headers: Dict[str, str],
    pr_author_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build the reviewer payload including reviewed files.

    This fetches the viewed state from the Contribution API and correlates it
    with the latest iteration's change tracking info to determine which files
    have been reviewed on the current version.

    Args:
        organization: Azure DevOps organization URL
        project: Project name
        repo_id: Repository ID
        pull_request_id: Pull request ID
        project_id: Project ID for Contribution API
        iterations_payload: List of PR iterations
        headers: Auth headers
        pr_author_id: Optional PR author's user ID. When provided and the current
            authenticated user matches this ID, the viewed-files check is skipped.
            This prevents the PR author's own file views from being misclassified
            as reviewer-reviewed files.
    """
    if not repo_id:
        return None

    # If the current user is the PR author, their "viewed" files are from
    # writing the code — not from reviewing. Skip the viewed-files check so
    # we don't incorrectly mark those files as already reviewed.
    if pr_author_id:
        current_user_id = _get_current_user_id(organization, headers)
        if current_user_id and current_user_id.lower() == pr_author_id.lower():
            print("Current user is the PR author; skipping viewed-files check to avoid false positives.")
            return None

    # Get the latest iteration ID
    latest_iteration_id = None
    if iterations_payload:
        sorted_iterations = sorted(iterations_payload, key=lambda x: x.get("id", 0))
        if sorted_iterations:
            latest_iteration_id = sorted_iterations[-1].get("id")

    # Get change tracking map for latest iteration
    change_tracking_map = _get_iteration_change_tracking_map(
        organization, project, repo_id, pull_request_id, latest_iteration_id, headers
    )

    # Get viewed files from Contribution API
    viewed_entries = _get_viewed_files_via_contribution(organization, project_id, repo_id, pull_request_id, headers)

    if not viewed_entries:
        return None

    # Filter viewed files to only include those that match the latest iteration
    reviewed_files: List[str] = []

    if change_tracking_map:
        # Filter by matching change tracking ID or object hash
        seen_paths: set = set()
        for entry in viewed_entries:
            path = entry.get("path")
            if not path or path in seen_paths:
                continue

            map_entry = change_tracking_map.get(path)
            if not map_entry:
                continue

            expected_tracking_id = map_entry.get("changeTrackingId", "")
            object_id = map_entry.get("objectId", "")
            entry_tracking_id = entry.get("changeTrackingId", "")
            entry_object_hash = entry.get("objectHash", "")

            # Match by change tracking ID
            if entry_tracking_id and expected_tracking_id:
                if entry_tracking_id.lower() == expected_tracking_id.lower():
                    reviewed_files.append(path)
                    seen_paths.add(path)
                    continue

            # Match by object hash (prefix match)
            if entry_object_hash and object_id:
                if object_id.lower().startswith(entry_object_hash.lower()):
                    reviewed_files.append(path)
                    seen_paths.add(path)
    else:
        # No change tracking map - include all viewed files
        reviewed_files = [e.get("path") for e in viewed_entries if e.get("path")]

    if not reviewed_files:
        return None

    return {
        "id": None,
        "vote": None,
        "reviewedFiles": reviewed_files,
    }


def get_pull_request_details() -> None:
    """
    Retrieve comprehensive pull request details including diff, threads, and reviewer state.

    State keys read:
        - pull_request_id (required): Pull request ID
        - dry_run: If true, only print what would be done

    Output:
        - Writes JSON to scripts/temp/temp-get-pull-request-details-response.json
        - Writes file details to scripts/temp/pull-request-review/prompts/<pull_request_id>/pull-request-files.json

    Raises:
        SystemExit: On validation or execution errors.
    """
    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()
    pull_request_id = get_pull_request_id(required=True)

    # Determine output paths
    temp_dir = get_state_dir()
    output_file = temp_dir / "temp-get-pull-request-details-response.json"
    prompts_root = temp_dir / "pull-request-review" / "prompts"

    # Ensure directories exist
    temp_dir.mkdir(parents=True, exist_ok=True)
    prompts_root.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print(f"DRY-RUN: Would retrieve pull request details for PR {pull_request_id}")
        print(f"  Organization: {config.organization}")
        print(f"  Project: {config.project}")
        print(f"  Repository: {config.repository}")
        print(f"  Output: {output_file}")
        return

    # Verify prerequisites
    verify_az_cli()
    pat = get_pat()

    # Set PAT for az CLI
    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Retrieving pull request details for PR {pull_request_id}...")

    # Get PR details via az CLI
    org_arg = (
        config.organization
        if config.organization.startswith("http")
        else f"https://dev.azure.com/{config.organization}"
    )

    result = run_safe(
        [
            "az",
            "repos",
            "pr",
            "show",
            "--id",
            str(pull_request_id),
            "--organization",
            org_arg,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        print(
            f"Error: Failed to get pull request details: {result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        pr_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse pull request response: {e}", file=sys.stderr)
        sys.exit(1)

    print("Pull request details retrieved successfully:")
    print(f"  PR ID: {pr_data.get('pullRequestId')}")
    print(f"  Title: {pr_data.get('title')}")
    print(f"  Is Draft: {pr_data.get('isDraft')}")
    print(f"  Status: {pr_data.get('status')}")

    if pr_data.get("autoCompleteSetBy"):
        print(f"  Auto-Complete: Set by {pr_data['autoCompleteSetBy'].get('displayName')}")
    else:
        print("  Auto-Complete: Not set")

    # Get auth headers for REST API calls
    headers = get_auth_headers(pat)

    # Extract branch info
    target_branch = normalize_ref_name(pr_data.get("targetRefName"))
    source_branch = normalize_ref_name(pr_data.get("sourceRefName"))
    base_commit = pr_data.get("lastMergeTargetCommit", {}).get("commitId")
    source_commit = pr_data.get("lastMergeSourceCommit", {}).get("commitId")

    base_ref = base_commit or (f"origin/{target_branch}" if target_branch else "origin/main")
    compare_ref = source_commit or (f"origin/{source_branch}" if source_branch else "HEAD")

    # Sync git refs
    if target_branch:
        sync_git_ref(f"origin/{target_branch}")
    if source_branch:
        sync_git_ref(f"origin/{source_branch}")

    # Get file diffs
    files_details = []
    diff_entries = get_diff_entries(base_ref, compare_ref)

    for entry in diff_entries:  # pragma: no cover
        added_info = get_added_lines_info(base_ref, compare_ref, entry.path)
        patch = None if added_info.is_binary else get_diff_patch(base_ref, compare_ref, entry.path)

        files_details.append(
            {
                "path": entry.path,
                "originalPath": entry.original_path,
                "status": entry.status,
                "changeType": entry.change_type,
                "isBinary": added_info.is_binary,
                "addedLineCount": len(added_info.lines),
                "addedLines": [{"line": line.line_number, "content": line.content} for line in added_info.lines],
                "patch": patch,
            }
        )

    comparison_info = {
        "baseRef": base_ref,
        "compareRef": compare_ref,
        "baseCommit": base_commit,
        "compareCommit": source_commit,
        "baseBranch": target_branch,
        "compareBranch": source_branch,
    }

    # Save files snapshot
    pull_request_prompt_dir = prompts_root / str(pull_request_id)
    pull_request_prompt_dir.mkdir(parents=True, exist_ok=True)
    files_snapshot_path = pull_request_prompt_dir / "pull-request-files.json"
    with open(files_snapshot_path, "w", encoding="utf-8") as f:
        json.dump({"files": files_details}, f, indent=2)

    # Fetch threads, iterations, reviewer data
    repo_id = pr_data.get("repository", {}).get("id")
    project_id = pr_data.get("repository", {}).get("project", {}).get("id")
    pr_author_id = pr_data.get("createdBy", {}).get("id")
    threads_payload = None
    iterations_payload = None
    reviewer_payload = None

    if repo_id:
        threads_payload = _get_pull_request_threads(
            config.organization, config.project, repo_id, pull_request_id, headers
        )
        iterations_payload = _get_pull_request_iterations(
            config.organization, config.project, repo_id, pull_request_id, headers
        )
        # Get reviewer payload with reviewed files info.
        # Pass pr_author_id so viewed-files from the PR author are not counted as reviews.
        reviewer_payload = _get_reviewer_payload(
            config.organization,
            config.project,
            repo_id,
            pull_request_id,
            project_id,
            iterations_payload,
            headers,
            pr_author_id=pr_author_id,
        )

    # Log reviewed files count if available
    reviewed_count = 0
    if reviewer_payload and reviewer_payload.get("reviewedFiles"):  # pragma: no cover
        reviewed_count = len(reviewer_payload["reviewedFiles"])

    print(f"Captured {len(files_details)} file entries for comparison.")
    if reviewed_count > 0:  # pragma: no cover
        print(f"Found {reviewed_count} files already reviewed on latest iteration.")

    # Build output payload
    output_payload = {
        "pullRequest": pr_data,
        "repository": pr_data.get("repository"),
        "comparison": comparison_info,
        "files": files_details,
        "threads": threads_payload,
        "iterations": iterations_payload,
        "reviewer": reviewer_payload,
    }

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"\nResponse (with file diffs) saved to: {output_file}")
