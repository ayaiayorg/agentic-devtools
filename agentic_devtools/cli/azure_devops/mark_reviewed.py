"""
Mark file as reviewed in Azure DevOps pull requests.

This module handles marking files as "reviewed" in Azure DevOps PRs by:
1. Updating the reviewer entry's reviewedFiles array via the Reviewers API
2. Syncing the viewed status via the Contribution API for UI display

The implementation mirrors the functionality of the original mark-file-reviewed.ps1.
"""

import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .auth import get_auth_headers, get_pat
from .config import AzureDevOpsConfig
from .helpers import require_requests

# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AuthenticatedUser:
    """Authenticated Azure DevOps user information."""

    display_name: Optional[str]
    descriptor: Optional[str]
    storage_key: Optional[str]
    subject_descriptor: Optional[str]


@dataclass
class ChangeEntry:
    """PR iteration change entry for a file."""

    change_tracking_id: int
    object_id: Optional[str]
    path: str


# =============================================================================
# Path Normalization
# =============================================================================


def normalize_repo_path(path: Optional[str]) -> Optional[str]:
    """Normalize a file path to repository format (/path/to/file)."""
    if not path or not path.strip():
        return None
    clean = path.strip().replace("\\", "/").strip("/")
    if not clean:
        return None
    return f"/{clean}"


# =============================================================================
# Azure DevOps API Helpers
# =============================================================================


def _get_connection_data(requests, headers: Dict[str, str], org_root: str) -> Dict[str, Any]:
    """
    Get Azure DevOps connection data including authenticated user info.

    Returns:
        Connection data dictionary with authenticatedUser, instanceId, etc.
    """
    connection_headers = dict(headers)
    connection_headers["Accept"] = "application/json;api-version=7.1-preview.1"

    url = f"{org_root}/_apis/connectionData?api-version=7.1-preview.1"
    response = requests.get(url, headers=connection_headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _extract_authenticated_user(connection_data: Dict[str, Any]) -> AuthenticatedUser:
    """Extract authenticated user info from connection data."""
    auth_user = connection_data.get("authenticatedUser", {})

    display_name = auth_user.get("providerDisplayName") or auth_user.get("customDisplayName")
    descriptor = auth_user.get("descriptor")
    storage_key = auth_user.get("storageKey") or auth_user.get("id")
    subject_descriptor = auth_user.get("subjectDescriptor")

    return AuthenticatedUser(
        display_name=display_name,
        descriptor=descriptor,
        storage_key=storage_key,
        subject_descriptor=subject_descriptor,
    )


def _get_organization_account_name(org_url: str) -> Optional[str]:
    """Extract organization account name from URL."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(org_url)
    except Exception:  # pragma: no cover
        return None

    # Check path first (e.g., https://dev.azure.com/swica -> swica)
    path = parsed.path.strip("/")
    if path:
        segments = [s for s in path.split("/") if s]
        if segments:
            return segments[-1]

    # Fall back to hostname (e.g., swica.visualstudio.com -> swica)
    host_parts = parsed.hostname.split(".") if parsed.hostname else []
    return host_parts[0] if host_parts else None


def _get_graph_api_root(org_root: str) -> str:
    """
    Get the Graph API root URL for Azure DevOps.

    For dev.azure.com URLs, the Graph API is at vssps.dev.azure.com.
    """
    import re

    if re.match(r"^https?://dev\.azure\.com", org_root):
        return re.sub(r"^https?://dev\.azure\.com", "https://vssps.dev.azure.com", org_root)
    return org_root


def _resolve_storage_key_via_graph(
    requests,
    headers: Dict[str, str],
    org_root: str,
    descriptor: str,
) -> Optional[str]:
    """
    Resolve storage key (GUID) for a user via the Graph API.

    The Reviewers API requires the storage key (GUID) as the identifier,
    not the descriptor. This function fetches the storage key from the
    Graph API when it's not available in the connection data.

    Args:
        requests: requests module
        headers: Authorization headers
        org_root: Organization root URL (e.g., https://dev.azure.com/swica)
        descriptor: User descriptor (e.g., aad.xxx or msa.xxx)

    Returns:
        Storage key (GUID) or None if resolution fails
    """
    graph_root = _get_graph_api_root(org_root)
    encoded_descriptor = quote(descriptor, safe="")
    url = f"{graph_root}/_apis/graph/users/{encoded_descriptor}?api-version=7.1-preview.1"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("storageKey")
    except Exception as e:
        print(f"Warning: Failed to resolve storage key for descriptor '{descriptor}': {e}")
        return None


def _get_project_id_via_api(
    requests,
    headers: Dict[str, str],
    org_root: str,
    project: str,
) -> str:
    """
    Get project ID using Azure DevOps REST API.

    This is preferred over subprocess calls to Azure CLI as it avoids
    potential hangs and is more reliable cross-platform.
    """
    project_encoded = quote(project, safe="")
    url = f"{org_root}/_apis/projects/{project_encoded}?api-version=7.1-preview.4"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    project_id = data.get("id")
    if not project_id:
        raise RuntimeError(f"Empty project ID returned for '{project}'")
    return project_id


def _get_reviewer_entry(
    requests,
    headers: Dict[str, str],
    org_root: str,
    project_encoded: str,
    repo_id: str,
    pull_request_id: int,
    reviewer_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get existing reviewer entry for the authenticated user.

    Returns:
        Reviewer entry dict or None if user is not yet a reviewer.
    """
    encoded_reviewer_id = quote(reviewer_id, safe="")
    url = (
        f"{org_root}/{project_encoded}/_apis/git/repositories/{repo_id}"
        f"/pullRequests/{pull_request_id}/reviewers/{encoded_reviewer_id}"
        "?api-version=7.2-preview.1"
    )

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Handle cases where user is not yet a reviewer
        status_code = e.response.status_code if e.response is not None else None
        treat_as_missing = False

        if status_code == 404:
            treat_as_missing = True
        elif status_code == 400:
            # Check for "Invalid argument value" in response body
            try:
                error_body = e.response.json() if e.response is not None else {}
                error_message = error_body.get("message", "")
                error_type = error_body.get("typeKey", "")
                if "invalid argument" in error_message.lower() or error_type == "InvalidArgumentValueException":
                    treat_as_missing = True
            except Exception:
                # Try raw text check as fallback
                try:
                    error_text = e.response.text if e.response is not None else ""
                    if "invalid argument" in error_text.lower():
                        treat_as_missing = True
                except Exception:  # pragma: no cover
                    pass

        if treat_as_missing:
            print("Current user is not yet a reviewer; will create reviewer entry.")
            return None
        raise
    except Exception as e:  # pragma: no cover
        # Generic fallback for other exceptions
        error_str = str(e).lower()
        if "404" in error_str or "invalid argument" in error_str:
            print("Current user is not yet a reviewer; will create reviewer entry.")
            return None
        raise


def _update_reviewer_entry(
    requests,
    headers: Dict[str, str],
    org_root: str,
    project_encoded: str,
    repo_id: str,
    pull_request_id: int,
    reviewer_id: str,
    existing_entry: Optional[Dict[str, Any]],
    updated_reviewed_files: List[str],
) -> None:
    """Update or create reviewer entry with updated reviewedFiles list."""
    encoded_reviewer_id = quote(reviewer_id, safe="")
    url = (
        f"{org_root}/{project_encoded}/_apis/git/repositories/{repo_id}"
        f"/pullRequests/{pull_request_id}/reviewers/{encoded_reviewer_id}"
        "?api-version=7.2-preview.1"
    )

    body = {
        "id": reviewer_id,
        "vote": existing_entry.get("vote", 0) if existing_entry else 0,
        "isFlagged": existing_entry.get("isFlagged", False) if existing_entry else False,
        "hasDeclined": existing_entry.get("hasDeclined", False) if existing_entry else False,
        "reviewedFiles": updated_reviewed_files,
    }

    headers_with_content = dict(headers)
    headers_with_content["Content-Type"] = "application/json"

    # Use PATCH if updating existing, PUT if creating new
    method = "PATCH" if existing_entry else "PUT"
    print(f"Updating reviewer entry via {method}...")

    try:
        if method == "PATCH":
            response = requests.patch(url, headers=headers_with_content, json=body, timeout=30)
        else:
            response = requests.put(url, headers=headers_with_content, json=body, timeout=30)

        response.raise_for_status()
        print("Reviewer entry updated successfully.")
    except Exception as e:
        print(f"Error during reviewer entry update: {e}")
        raise


# =============================================================================
# Viewed Status Sync (Contribution API)
# =============================================================================


def _get_existing_viewed_state_tokens(
    requests,
    headers: Dict[str, str],
    org_root: str,
    project_id: str,
    repo_id: str,
    pull_request_id: int,
) -> List[str]:
    """
    Get existing viewed state tokens from the PR visit data provider.

    These tokens track which files have been "viewed" in the PR UI.
    """
    headers_with_content = dict(headers)
    headers_with_content["Content-Type"] = "application/json"

    url = f"{org_root}/_apis/Contribution/HierarchyQuery/project/{project_id}?api-version=7.1-preview.1"

    payload = {
        "contributionIds": ["ms.vss-code-web.pr-detail-visit-data-provider"],
        "dataProviderContext": {
            "properties": {
                "repositoryId": repo_id,
                "pullRequestId": pull_request_id,
            }
        },
    }

    try:
        response = requests.post(url, headers=headers_with_content, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    provider = data.get("dataProviders", {}).get("ms.vss-code-web.pr-detail-visit-data-provider", {})
    visit = provider.get("visit", {})
    viewed_state_str = visit.get("viewedState")

    if not viewed_state_str:
        return []

    # viewedState is a JSON string that needs to be parsed
    import json

    try:
        viewed_state = json.loads(viewed_state_str)
    except (json.JSONDecodeError, TypeError):
        return []

    hashes = viewed_state.get("hashes", {})
    return list(hashes.keys()) if isinstance(hashes, dict) else []


def _get_iteration_change_entry(
    requests,
    headers: Dict[str, str],
    base_url: str,
    target_path: str,
) -> Optional[ChangeEntry]:
    """
    Find the change entry for a file across PR iterations.

    Returns:
        ChangeEntry with objectId and changeTrackingId, or None if not found.
    """
    target_lower = target_path.lower()
    next_url = f"{base_url}&$top=200"

    while next_url:
        response = requests.get(next_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        entries = data.get("value", []) or data.get("changeEntries", [])

        for entry in entries:
            item = entry.get("item", {})
            entry_path = item.get("path", "")
            if entry_path and entry_path.lower() == target_lower:
                change_tracking_id = entry.get("changeTrackingId")
                object_id = item.get("objectId")
                if change_tracking_id:
                    return ChangeEntry(
                        change_tracking_id=change_tracking_id,
                        object_id=object_id,
                        path=entry_path,
                    )

        # Handle pagination
        next_link = data.get("nextLink")
        continuation_token = data.get("continuationToken")

        if next_link:  # pragma: no cover
            next_url = next_link
        elif continuation_token:  # pragma: no cover
            next_url = f"{base_url}&continuationToken={quote(continuation_token, safe='')}"
        else:
            next_url = None

    return None


def _sync_viewed_status(
    requests,
    headers: Dict[str, str],
    org_root: str,
    project: str,
    project_id: str,
    repository: str,
    repo_id: str,
    pull_request_id: int,
    normalized_path: str,
    organization_account_name: Optional[str],
    instance_id: Optional[str],
    existing_hash_tokens: List[str],
) -> None:
    """
    Sync the viewed status for a file via the Contribution API.

    This makes the file appear as "viewed" (eye icon) in the Azure DevOps PR UI.
    """
    project_encoded = quote(project, safe="")

    # Get iterations to find the change entry
    iterations_url = (
        f"{org_root}/{project_encoded}/_apis/git/repositories/{repo_id}"
        f"/pullRequests/{pull_request_id}/iterations?api-version=7.1-preview.1"
    )

    response = requests.get(iterations_url, headers=headers, timeout=30)
    response.raise_for_status()
    iterations_data = response.json()

    iterations = iterations_data.get("value", [])
    if not iterations:
        print("Unable to resolve pull request iterations for viewed status sync.")
        return

    # Sort by ID descending to check most recent first
    iterations = sorted(iterations, key=lambda x: int(x.get("id", 0)), reverse=True)

    # Find change entry for the file
    change_entry = None
    for iteration in iterations:
        iteration_id = iteration.get("id")
        if not iteration_id:  # pragma: no cover
            continue

        base_changes_url = (
            f"{org_root}/{project_encoded}/_apis/git/repositories/{repo_id}"
            f"/pullRequests/{pull_request_id}/iterations/{iteration_id}/changes"
            "?api-version=7.1-preview.1"
        )

        change_entry = _get_iteration_change_entry(requests, headers, base_changes_url, normalized_path)
        if change_entry:
            break

    if not change_entry:
        print(f"Unable to find change entry for '{normalized_path}'; skipping viewed status sync.")
        return

    if not change_entry.object_id:
        print("Change entry missing object hash; skipping viewed status sync.")
        return

    # Build modify-hash tokens
    path_without_leading = normalized_path.lstrip("/")
    tokens_from_existing = []

    normalized_lower = normalized_path.lower()
    trimmed_lower = path_without_leading.lower()

    for token in existing_hash_tokens:
        if not token:
            continue  # pragma: no cover
        token_lower = token.lower()
        if token_lower.endswith(f"@{normalized_lower}") or (
            trimmed_lower and token_lower.endswith(f"@{trimmed_lower}")
        ):
            tokens_from_existing.append(token)

    # Generate token from object ID
    generated_token = None
    if change_entry.object_id:
        upper_object_id = change_entry.object_id.upper()
        hash_prefix_length = min(8, len(upper_object_id))
        hash_prefix = upper_object_id[:hash_prefix_length]
        generated_token = f"1@{hash_prefix}@{normalized_path}"

    unique_tokens = []
    if generated_token:  # pragma: no cover
        unique_tokens = [generated_token]
    elif tokens_from_existing:
        # Prefer tokens starting with "1@"
        preferred = [t for t in tokens_from_existing if t.startswith("1@")]
        unique_tokens = list(set(preferred or tokens_from_existing))

    if not unique_tokens:  # pragma: no cover
        print(f"Unable to build modify-hash tokens for '{normalized_path}'; skipping viewed status sync.")
        return

    # Build source page for routing
    source_page = None
    if project and repository:
        route_values = {
            "project": project,
            "GitRepositoryName": repository,
            "parameters": str(pull_request_id),
            "vctype": "git",
            "controller": "ContributedPage",
            "action": "Execute",
        }
        if instance_id:
            service_host = f"{instance_id} ({organization_account_name})" if organization_account_name else instance_id
            route_values["serviceHost"] = service_host

        source_page = {
            "url": f"{org_root}/{project}/_git/{repository}/pullrequest/{pull_request_id}?_a=files",
            "routeId": "ms.vss-code-web.pull-request-details-route",
            "routeValues": route_values,
        }

    # Build contribution payload
    properties: Dict[str, Any] = {
        "repositoryId": repo_id,
        "pullRequestId": pull_request_id,
        "projectId": project_id,
        "modifyViewedStatus": 2,  # Mark as viewed
        "modifyHashes": unique_tokens,
    }
    if source_page:
        properties["sourcePage"] = source_page

    contribution_url = f"{org_root}/_apis/Contribution/HierarchyQuery/project/{project_id}?api-version=7.1-preview.1"

    payload = {
        "contributionIds": ["ms.vss-code-web.pr-detail-visit-data-provider"],
        "dataProviderContext": {"properties": properties},
    }

    headers_with_content = dict(headers)
    headers_with_content["Content-Type"] = "application/json"

    print(f"Syncing viewed status for '{normalized_path}' via Contribution API...")
    response = requests.post(contribution_url, headers=headers_with_content, json=payload, timeout=30)
    response.raise_for_status()


# =============================================================================
# Main Entry Point
# =============================================================================


def mark_file_reviewed(  # pragma: no cover
    file_path: str,
    pull_request_id: int,
    config: AzureDevOpsConfig,
    repo_id: str,
    dry_run: bool = False,
) -> bool:
    """
    Mark a file as reviewed in an Azure DevOps pull request.

    This updates both:
    1. The reviewer's reviewedFiles list (API-level tracking)
    2. The viewed status in the UI (Contribution API)

    Args:
        file_path: Path of file to mark as reviewed
        pull_request_id: Pull request ID
        config: Azure DevOps configuration
        repo_id: Repository ID
        dry_run: If True, only print what would be done

    Returns:
        True if successful, False otherwise
    """
    normalized_path = normalize_repo_path(file_path)
    if not normalized_path:
        print(f"Error: Invalid file path '{file_path}'", file=sys.stderr)
        return False

    org_root = config.organization.rstrip("/")
    if not org_root.startswith("http"):  # pragma: no cover
        org_root = f"https://dev.azure.com/{org_root}"

    project_encoded = quote(config.project, safe="")

    if dry_run:
        print(f"DRY-RUN: Would mark '{normalized_path}' as reviewed on PR {pull_request_id}.")
        return True

    # Only require requests and PAT for actual execution
    requests = require_requests()
    pat = get_pat()
    headers = get_auth_headers(pat)

    # Get authenticated user details
    print("Retrieving authenticated user details...")
    try:
        connection_data = _get_connection_data(requests, headers, org_root)
    except Exception as e:
        print(f"Failed to retrieve Azure DevOps connection data: {e}", file=sys.stderr)
        return False

    auth_user = _extract_authenticated_user(connection_data)
    instance_id = connection_data.get("instanceId")
    organization_account_name = _get_organization_account_name(org_root)

    # Determine reviewer identifier - must be storage key (GUID), not descriptor
    # The Reviewers API requires the storage key as the identifier
    reviewer_id = auth_user.storage_key

    # If no storage key in connection data, try to resolve via Graph API
    if not reviewer_id:
        # Try subject_descriptor first, then descriptor
        descriptor_to_resolve = auth_user.subject_descriptor or auth_user.descriptor
        if descriptor_to_resolve:  # pragma: no cover
            print(f"Resolving storage key via Graph API for descriptor: {descriptor_to_resolve}")
            reviewer_id = _resolve_storage_key_via_graph(requests, headers, org_root, descriptor_to_resolve)

    if not reviewer_id:
        print("Unable to resolve reviewer identity (storage key) for current user.", file=sys.stderr)
        return False

    identity_summary = f"Authenticated as '{auth_user.display_name or reviewer_id}'"
    if auth_user.descriptor:  # pragma: no cover
        identity_summary += f" (descriptor: {auth_user.descriptor})"
    if reviewer_id:
        identity_summary += f" (storageKey: {reviewer_id})"
    print(identity_summary)

    # Get existing reviewer entry
    try:
        reviewer_entry = _get_reviewer_entry(
            requests, headers, org_root, project_encoded, repo_id, pull_request_id, reviewer_id
        )
    except Exception as e:
        print(f"Failed to retrieve reviewer entry: {e}", file=sys.stderr)
        return False

    # Check if already reviewed
    existing_reviewed = reviewer_entry.get("reviewedFiles", []) if reviewer_entry else []
    if normalized_path in existing_reviewed:
        print(f"File '{normalized_path}' already marked as reviewed.")
        return True

    # Update reviewer entry with new file
    updated_reviewed = list(set(existing_reviewed + [normalized_path]))

    try:
        _update_reviewer_entry(
            requests,
            headers,
            org_root,
            project_encoded,
            repo_id,
            pull_request_id,
            reviewer_id,
            reviewer_entry,
            updated_reviewed,
        )
    except Exception as e:
        print(f"Failed to update reviewer entry: {e}", file=sys.stderr)
        return False

    # Get project ID for Contribution API
    try:
        project_id = _get_project_id_via_api(requests, headers, org_root, config.project)
    except Exception as e:
        print(f"Warning: Could not get project ID for viewed status sync: {e}")
        project_id = None

    # Sync viewed status via Contribution API (best effort)
    if project_id:
        try:
            existing_tokens = _get_existing_viewed_state_tokens(
                requests, headers, org_root, project_id, repo_id, pull_request_id
            )
        except Exception:
            existing_tokens = []

        try:
            _sync_viewed_status(
                requests,
                headers,
                org_root,
                config.project,
                project_id,
                config.repository,
                repo_id,
                pull_request_id,
                normalized_path,
                organization_account_name,
                instance_id,
                existing_tokens,
            )
        except Exception as e:
            print(f"Warning: Failed to sync viewed status: {e}")

    print(f"Marked '{normalized_path}' as reviewed.")
    return True


# =============================================================================
# CLI Entry Point
# =============================================================================


def mark_file_reviewed_cli() -> None:
    """
    CLI command to mark a file as reviewed in a pull request.

    State keys read:
        - pull_request_id (required): Pull request ID
        - file_review.file_path (required): Path of file to mark as reviewed
        - dry_run: If true, only print what would be done

    Usage:
        agdt-set pull_request_id 23580
        agdt-set file_review.file_path "/path/to/file.ts"
        agdt-mark-file-reviewed
    """
    from ...state import get_pull_request_id, get_value, is_dry_run
    from .helpers import get_repository_id

    config = AzureDevOpsConfig.from_state()
    dry_run = is_dry_run()
    pull_request_id = get_pull_request_id(required=True)

    file_path = get_value("file_review.file_path")
    if not file_path:
        print("Error: 'file_review.file_path' is required.", file=sys.stderr)
        print("Set it with: agdt-set file_review.file_path <path>", file=sys.stderr)
        sys.exit(1)

    repo_id = get_repository_id(config.organization, config.project, config.repository)

    success = mark_file_reviewed(
        file_path=file_path,
        pull_request_id=pull_request_id,
        config=config,
        repo_id=repo_id,
        dry_run=dry_run,
    )

    if not success:
        sys.exit(1)
