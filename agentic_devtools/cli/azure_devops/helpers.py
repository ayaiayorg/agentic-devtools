"""
Azure DevOps helper functions.

Pure utility functions that don't read state directly.
"""

import json
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

from ..subprocess_utils import run_safe
from .config import (
    APPROVAL_SENTINEL,
    DEFAULT_ORGANIZATION,
    DEFAULT_PROJECT,
    DEFAULT_REPOSITORY,
    AzureDevOpsConfig,
)


def parse_bool_from_state_value(raw_value, default: bool = False) -> bool:
    """
    Parse a boolean value from a raw state value.

    Args:
        raw_value: The value from state (could be None, bool, or str).
        default: Default value if raw_value is None.

    Returns:
        Boolean value parsed from input.
    """
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).lower() in ("1", "true", "yes")


def require_requests():
    """Import and return requests module, exiting if not available."""
    try:
        import requests

        return requests
    except ImportError:
        print(
            "Error: requests library required. Install with: pip install requests",
            file=sys.stderr,
        )
        sys.exit(1)


def get_repository_id(
    organization: str = DEFAULT_ORGANIZATION,
    project: str = DEFAULT_PROJECT,
    repository: str = DEFAULT_REPOSITORY,
) -> str:
    """Get the repository ID using Azure CLI."""
    cmd = [
        "az",
        "repos",
        "show",
        "--organization",
        organization,
        "--project",
        project,
        "--repository",
        repository,
        "--query",
        "id",
        "--output",
        "tsv",
    ]

    result = run_safe(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Failed to get repository ID for '{repository}': {result.stderr}")

    repo_id = result.stdout.strip()
    if not repo_id:
        raise RuntimeError(f"Empty repository ID returned for '{repository}'")

    return repo_id


def resolve_thread_by_id(
    requests_module,
    headers: Dict[str, str],
    config: AzureDevOpsConfig,
    repo_id: str,
    pull_request_id: int,
    thread_id: int,
    status: str = "closed",
) -> None:
    """
    Resolve a pull request thread by setting its status.

    Args:
        requests_module: The requests module.
        headers: Auth headers for API calls.
        config: Azure DevOps configuration.
        repo_id: Repository ID.
        pull_request_id: Pull request ID.
        thread_id: Thread ID to resolve.
        status: Status to set ("closed", "fixed", etc.).
    """
    resolve_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads", thread_id)
    response = requests_module.patch(resolve_url, headers=headers, json={"status": status})
    response.raise_for_status()


def convert_to_pull_request_title(title: str) -> str:
    """
    Strip Markdown links from a title to match pull request title convention.

    Transforms commit-style titles with Markdown links to clean PR titles:
    - feature([DFLY-1234](link)): summary -> feature(DFLY-1234): summary
    - feature([DFLY-1234](link) / [DFLY-5678](link)): summary -> feature(DFLY-1234/DFLY-5678): summary

    Args:
        title: The title string potentially containing Markdown links.

    Returns:
        String with Markdown links stripped.
    """
    # Remove (link) parts: [text](link) -> [text]
    result = re.sub(r"\]\([^)]+\)", "]", title)
    # Remove brackets: [text] -> text
    result = re.sub(r"\[([^\]]+)\]", r"\1", result)
    # Remove spaces around slash: text / text -> text/text
    result = re.sub(r"\s*/\s*", "/", result)
    return result


def format_approval_content(content: str) -> str:
    """
    Wrap content with approval sentinel banners.

    Args:
        content: The comment content to wrap.

    Returns:
        Content wrapped with approval sentinels, or unchanged if already formatted.
    """
    trimmed = content.strip()
    if trimmed.startswith(APPROVAL_SENTINEL) and trimmed.endswith(APPROVAL_SENTINEL):
        return trimmed  # Already formatted
    return f"{APPROVAL_SENTINEL}\n\n{trimmed}\n\n{APPROVAL_SENTINEL}\n\n"


def build_thread_context(
    path: Optional[str],
    line: Optional[int],
    end_line: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    Build thread context for file-level PR comments.

    Args:
        path: File path for the comment.
        line: Start line number.
        end_line: End line number (defaults to line if not specified).

    Returns:
        Thread context dict or None if no path specified.
    """
    if not path:
        return None

    thread_context: Dict[str, Any] = {"filePath": path}

    if line is not None:
        # For line comments, we need right-side positioning (after changes)
        thread_context["rightFileStart"] = {"line": int(line), "offset": 1}
        end = int(end_line) if end_line is not None else int(line)
        thread_context["rightFileEnd"] = {"line": end, "offset": 1}

    return thread_context


def verify_az_cli() -> None:
    """Verify Azure CLI and azure-devops extension are installed."""
    try:
        run_safe(["az", "--version"], capture_output=True, check=True, shell=True)  # nosec B604 - shell=True required to locate az CLI via PATH on all platforms
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Azure CLI (az) is not installed or not in PATH.", file=sys.stderr)
        print(
            "Install it from: https://learn.microsoft.com/cli/azure/install-azure-cli",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check for azure-devops extension
    result = run_safe(
        [
            "az",
            "extension",
            "list",
            "--output",
            "tsv",
            "--query",
            "[?name=='azure-devops'].name",
        ],
        capture_output=True,
        text=True,
        shell=True,  # nosec B604 - shell=True required to locate az CLI via PATH on all platforms
    )
    if not result.stdout.strip():
        print(
            "Error: Azure CLI extension 'azure-devops' is not installed.",
            file=sys.stderr,
        )
        print("Run: az extension add --name azure-devops", file=sys.stderr)
        sys.exit(1)


def parse_json_response(response_text: str, context: str) -> Dict[str, Any]:
    """Parse JSON response, exiting with error on failure."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        print(f"Error parsing {context}: {response_text}", file=sys.stderr)
        sys.exit(1)


def print_threads(threads: List[Dict[str, Any]]) -> None:
    """Format and print PR threads."""
    print(f"\nFound {len(threads)} thread(s):\n")

    for thread in threads:
        thread_id = thread.get("id")
        status = thread.get("status", "unknown")
        thread_context = thread.get("threadContext") or {}
        file_path = thread_context.get("filePath", "(general comment)")

        print(f"--- Thread {thread_id} [{status}] ---")
        print(f"File: {file_path}")

        comments = thread.get("comments", [])
        for comment in comments:
            author = (comment.get("author") or {}).get("displayName", "Unknown")
            content = comment.get("content", "(no content)")
            comment_id = comment.get("id")
            # Truncate long content
            content_preview = content[:100] + "..." if len(content) > 100 else content
            print(f"  [{comment_id}] {author}: {content_preview}")

        print()


def find_pull_request_by_issue_key(
    issue_key: str,
    config: Optional[AzureDevOpsConfig] = None,
    headers: Optional[Dict[str, str]] = None,
    status: str = "active",
) -> Optional[Dict[str, Any]]:
    """
    Find a pull request by Jira issue key in the source branch, title, or description.

    This searches Azure DevOps for active PRs (including drafts) where the issue key
    appears in the source branch name, PR title, or PR description.

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        config: Azure DevOps configuration (defaults to from_state)
        headers: Auth headers (defaults to get_auth_headers)
        status: PR status filter ("active", "completed", "abandoned", "all")

    Returns:
        Pull request data dict if found, None otherwise.
        If multiple PRs match, returns the most recently created one.
    """
    requests = require_requests()

    if config is None:
        config = AzureDevOpsConfig.from_state()

    if headers is None:
        from .auth import get_auth_headers, get_pat

        pat = get_pat()  # pragma: no cover
        headers = get_auth_headers(pat)  # pragma: no cover

    # Get repository ID using config values
    try:
        repo_id = get_repository_id(
            organization=config.organization,
            project=config.project,
            repository=config.repository,
        )
    except RuntimeError as e:  # pragma: no cover
        print(f"Error: {e}", file=sys.stderr)
        return None

    # Build search URL - search by status only, we'll filter locally
    project_encoded = config.project.replace(" ", "%20")
    url = (
        f"{config.organization}/{project_encoded}/_apis/git/repositories/"
        f"{repo_id}/pullrequests?searchCriteria.status={status}&api-version=7.0"
    )

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Error: Failed to search PRs: {response.status_code}", file=sys.stderr)
            return None

        data = response.json()
        pull_requests = data.get("value", [])

        # Filter PRs by issue key in source branch, title, or description (case-insensitive)
        issue_key_lower = issue_key.lower()
        matching_prs = []

        for pr in pull_requests:
            # Check source branch
            source_ref = pr.get("sourceRefName", "")
            branch_name = source_ref.replace("refs/heads/", "")

            # Check title
            title = pr.get("title", "")

            # Check description
            description = pr.get("description", "") or ""

            # Match if issue key appears in any of these fields
            if (
                issue_key_lower in branch_name.lower()
                or issue_key_lower in title.lower()
                or issue_key_lower in description.lower()
            ):
                matching_prs.append(pr)

        if not matching_prs:
            return None

        # If multiple matches, return the most recently created
        if len(matching_prs) > 1:
            # Sort by creation date descending
            matching_prs.sort(
                key=lambda x: x.get("creationDate", ""),
                reverse=True,
            )
            print(
                f"Found {len(matching_prs)} PRs matching '{issue_key}', "
                f"using most recent: #{matching_prs[0].get('pullRequestId')}",
            )

        return matching_prs[0]

    except Exception as e:  # pragma: no cover
        print(f"Error searching for PRs: {e}", file=sys.stderr)
        return None


def get_pull_request_details(
    pull_request_id: int,
    config: Optional[AzureDevOpsConfig] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get full details for a pull request.

    Args:
        pull_request_id: Pull request ID
        config: Azure DevOps configuration (defaults to from_state)
        headers: Auth headers (defaults to get_auth_headers)

    Returns:
        Pull request data dict if found, None otherwise.
    """
    requests = require_requests()

    if config is None:
        config = AzureDevOpsConfig.from_state()

    if headers is None:
        from .auth import get_auth_headers, get_pat

        pat = get_pat()  # pragma: no cover
        headers = get_auth_headers(pat)  # pragma: no cover

    # Get repository ID using config values
    try:
        repo_id = get_repository_id(
            organization=config.organization,
            project=config.project,
            repository=config.repository,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

    # Build URL to get PR details
    project_encoded = config.project.replace(" ", "%20")
    url = (
        f"{config.organization}/{project_encoded}/_apis/git/repositories/"
        f"{repo_id}/pullrequests/{pull_request_id}?api-version=7.0"
    )

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Error: Failed to get PR #{pull_request_id}: {response.status_code}", file=sys.stderr)
            return None

        return response.json()

    except Exception as e:
        print(f"Error getting PR details: {e}", file=sys.stderr)
        return None


def get_pull_request_source_branch(
    pull_request_id: int,
    config: Optional[AzureDevOpsConfig] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Get the source branch name for a pull request.

    Args:
        pull_request_id: Pull request ID
        config: Azure DevOps configuration (defaults to from_state)
        headers: Auth headers (defaults to get_auth_headers)

    Returns:
        Source branch name (without refs/heads/ prefix) if found, None otherwise.
    """
    # Use get_pull_request_details to fetch full PR data
    data = get_pull_request_details(pull_request_id, config, headers)
    if not data:
        return None

    source_ref = data.get("sourceRefName", "")

    # Strip refs/heads/ prefix if present
    if source_ref.startswith("refs/heads/"):
        return source_ref[len("refs/heads/") :]

    return source_ref if source_ref else None


def find_jira_issue_from_pr(
    pull_request_id: int,
    config: Optional[AzureDevOpsConfig] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Find Jira issue key from a pull request.

    Searches for Jira issue key (e.g., DFLY-1234) in:
    1. PR source branch name (e.g., feature/DFLY-1234/my-feature)
    2. PR title
    3. PR description

    Args:
        pull_request_id: Pull request ID
        config: Azure DevOps configuration (defaults to from_state)
        headers: Auth headers (defaults to get_auth_headers)

    Returns:
        Jira issue key (e.g., "DFLY-1234") if found, None otherwise.
    """
    import re

    # Pattern to match Jira issue keys (DFLY-1234, etc.)
    jira_pattern = re.compile(r"(DFLY-\d+)", re.IGNORECASE)

    # Get full PR details
    pr_details = get_pull_request_details(pull_request_id, config, headers)
    if not pr_details:
        return None

    # 1. Check source branch first (most reliable)
    source_ref = pr_details.get("sourceRefName", "")
    branch_name = source_ref.replace("refs/heads/", "")
    if branch_name:
        match = jira_pattern.search(branch_name)
        if match:
            return match.group(1).upper()

    # 2. Check PR title
    title = pr_details.get("title", "")
    if title:
        match = jira_pattern.search(title)
        if match:
            return match.group(1).upper()

    # 3. Check PR description
    description = pr_details.get("description", "") or ""
    if description:
        match = jira_pattern.search(description)
        if match:
            return match.group(1).upper()

    return None


def find_pr_from_jira_issue(
    issue_key: str,
    config: Optional[AzureDevOpsConfig] = None,
    headers: Optional[Dict[str, str]] = None,
    verbose: bool = False,
) -> Optional[int]:
    """
    Find active PR from a Jira issue key.

    Searches multiple sources in order of reliability:
    1. Jira Development panel (most reliable - official Azure DevOps integration)
    2. Azure DevOps PRs where issue key appears in branch/title/description
    3. Jira issue comments/description for PR links (least reliable - text patterns)

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        config: Azure DevOps configuration (defaults to from_state)
        headers: Auth headers (defaults to get_auth_headers)
        verbose: Whether to print debug output

    Returns:
        PR ID as integer if found, None otherwise.
    """
    # 1. First, try Jira Development panel (most reliable - official integration)
    try:
        from .review_jira import get_pr_from_development_panel

        dev_panel_pr_id = get_pr_from_development_panel(issue_key, verbose=verbose)
        if dev_panel_pr_id:
            if verbose:  # pragma: no cover
                print(f"Found PR #{dev_panel_pr_id} in Jira Development panel")
            return dev_panel_pr_id
    except Exception:
        # Development panel lookup failed, continue to ADO search
        pass

    # 2. Second, search Azure DevOps for PR with issue key in branch/title/description
    pr_data = find_pull_request_by_issue_key(issue_key, config, headers)
    if pr_data:
        pr_id = pr_data.get("pullRequestId")
        if pr_id:
            if verbose:  # pragma: no cover
                print(f"Found PR #{pr_id} via Azure DevOps search")
            return int(pr_id)

    # 3. Last resort: text pattern matching in Jira comments/description
    try:
        from .review_jira import get_linked_pull_request_from_jira

        jira_pr_id = get_linked_pull_request_from_jira(issue_key, verbose=verbose)
        if jira_pr_id:
            if verbose:  # pragma: no cover
                print(f"Found PR #{jira_pr_id} via text pattern in Jira")
            return jira_pr_id
    except Exception:  # pragma: no cover
        # Jira lookup failed
        pass

    return None
