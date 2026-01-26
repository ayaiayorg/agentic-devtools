"""
Jira integration for PR review workflow.

Functions for fetching Jira issues and extracting linked PRs.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

import requests

# Environment variables for Jira API
JIRA_COPILOT_PAT_ENV = "JIRA_COPILOT_PAT"
JIRA_BASE_URL_ENV = "JIRA_BASE_URL"
JIRA_BASE_URL_DEFAULT = "https://jira.swica.ch"


def get_jira_credentials() -> Tuple[Optional[str], str]:
    """
    Get Jira credentials from environment.

    Returns:
        Tuple of (PAT token or None, base URL)
    """
    pat = os.environ.get(JIRA_COPILOT_PAT_ENV)
    base_url = os.environ.get(JIRA_BASE_URL_ENV, JIRA_BASE_URL_DEFAULT).rstrip("/")
    return pat, base_url


def fetch_jira_issue(issue_key: str, verbose: bool = False) -> Optional[Dict]:
    """
    Fetch Jira issue details via REST API.

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        verbose: Whether to print debug output

    Returns:
        Issue data dictionary or None if fetch failed
    """
    pat, base_url = get_jira_credentials()

    if not pat:
        if verbose:
            print(f"Warning: {JIRA_COPILOT_PAT_ENV} not set, cannot fetch Jira issue")
        return None

    url = f"{base_url}/rest/api/2/issue/{issue_key}"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {pat}", "Accept": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        elif verbose:
            print(f"Warning: Jira API returned {response.status_code} for {issue_key}")

    except requests.RequestException as e:
        if verbose:
            print(f"Warning: Failed to fetch Jira issue: {e}")

    return None


def fetch_development_panel_prs(issue_key: str, verbose: bool = False) -> List[Dict]:
    """
    Fetch PRs from Jira Development panel via the dev-status API.

    This API returns PRs that are automatically linked via Azure DevOps/GitHub
    integration (the "Development" panel in Jira UI).

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        verbose: Whether to print debug output

    Returns:
        List of PR dictionaries from the development panel, empty list if none found
    """
    pat, base_url = get_jira_credentials()

    if not pat:
        if verbose:
            print(f"Warning: {JIRA_COPILOT_PAT_ENV} not set, cannot fetch development panel")
        return []

    # The dev-status API requires the issue ID (numeric), not the key
    # First fetch the issue to get the ID
    issue_url = f"{base_url}/rest/api/2/issue/{issue_key}?fields=id"

    try:
        issue_response = requests.get(
            issue_url,
            headers={"Authorization": f"Bearer {pat}", "Accept": "application/json"},
            timeout=30,
        )

        if issue_response.status_code != 200:
            if verbose:
                print(f"Warning: Failed to fetch issue ID: {issue_response.status_code}")
            return []

        issue_id = issue_response.json().get("id")
        if not issue_id:
            if verbose:
                print("Warning: Issue ID not found in response")
            return []

        # Now fetch the development panel data
        dev_url = (
            f"{base_url}/rest/dev-status/1.0/issue/detail?issueId={issue_id}&applicationType=stash&dataType=pullrequest"
        )

        dev_response = requests.get(
            dev_url,
            headers={"Authorization": f"Bearer {pat}", "Accept": "application/json"},
            timeout=30,
        )

        if dev_response.status_code != 200:
            if verbose:
                print(f"Warning: Dev-status API returned {dev_response.status_code}")
            return []

        dev_data = dev_response.json()

        # Extract PRs from the response structure
        # The response has a "detail" array with provider data
        pull_requests = []
        for detail in dev_data.get("detail", []):
            for pr in detail.get("pullRequests", []):
                pull_requests.append(pr)

        if verbose and pull_requests:
            print(f"Found {len(pull_requests)} PR(s) in Development panel")

        return pull_requests

    except requests.RequestException as e:
        if verbose:
            print(f"Warning: Failed to fetch development panel: {e}")
        return []


def extract_pr_id_from_development_panel(pull_requests: List[Dict]) -> Optional[int]:
    """
    Extract Azure DevOps PR ID from development panel PR data.

    Args:
        pull_requests: List of PR dictionaries from fetch_development_panel_prs

    Returns:
        PR ID as integer, or None if not found
    """
    if not pull_requests:
        return None

    # Pattern to extract PR ID from Azure DevOps URLs
    # Example: https://dev.azure.com/org/project/_git/repo/pullrequest/1234
    ado_pr_pattern = re.compile(r"/pullrequest/(\d+)", re.IGNORECASE)

    for pr in pull_requests:
        url = pr.get("url", "")
        if url:
            match = ado_pr_pattern.search(url)
            if match:
                return int(match.group(1))

        # Some integrations may have the ID directly
        pr_id = pr.get("id")
        if pr_id and isinstance(pr_id, (int, str)):
            # Try to extract numeric ID if it's a string like "#1234" or "1234"
            if isinstance(pr_id, int):
                return pr_id
            numeric_match = re.search(r"(\d+)", str(pr_id))
            if numeric_match:
                return int(numeric_match.group(1))

    return None


def extract_linked_pr_from_issue(issue_data: Dict) -> Optional[int]:
    """
    Extract linked Azure DevOps PR ID from Jira issue comments/description.

    This is a fallback method that looks for PR links in text with pattern:
    - Pull Request #1234
    - PR: #1234
    - *PR:* #1234

    Note: This is less reliable than the Development panel API.

    Args:
        issue_data: Jira issue data dictionary

    Returns:
        PR ID as integer, or None if not found
    """
    if not issue_data:
        return None

    # Pattern to match PR references
    pr_pattern = re.compile(r"(?:Pull Request|PR:?\*?)\s*#?(\d+)", re.IGNORECASE)

    # Check comments
    comment_data = issue_data.get("fields", {}).get("comment", {})
    comments = comment_data.get("comments", []) if isinstance(comment_data, dict) else []

    for comment in reversed(comments):  # Check newest first
        body = comment.get("body", "")
        match = pr_pattern.search(body)
        if match:
            return int(match.group(1))

    # Check description as fallback
    description = issue_data.get("fields", {}).get("description", "")
    if description:
        match = pr_pattern.search(description)
        if match:
            return int(match.group(1))

    return None


def get_linked_pull_request_from_jira(issue_key: str, verbose: bool = False) -> Optional[int]:
    """
    Get linked PR ID from a Jira issue using text pattern matching.

    This searches comments and description for PR references like "PR: #1234".
    This is a fallback method - prefer using find_pr_from_jira_issue() which
    checks the Development panel first.

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        verbose: Whether to print debug output

    Returns:
        PR ID as integer, or None if not found
    """
    issue_data = fetch_jira_issue(issue_key, verbose)
    if not issue_data:
        return None

    return extract_linked_pr_from_issue(issue_data)


def get_pr_from_development_panel(issue_key: str, verbose: bool = False) -> Optional[int]:
    """
    Get linked PR ID from Jira Development panel.

    This is the most reliable source as it uses the official Azure DevOps
    integration data.

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        verbose: Whether to print debug output

    Returns:
        PR ID as integer, or None if not found
    """
    pull_requests = fetch_development_panel_prs(issue_key, verbose)
    return extract_pr_id_from_development_panel(pull_requests)


def display_jira_issue_summary(issue_data: Dict) -> None:
    """
    Print a formatted summary of a Jira issue.

    Args:
        issue_data: Jira issue data dictionary
    """
    if not issue_data:
        return

    fields = issue_data.get("fields", {})
    key = issue_data.get("key", "Unknown")
    summary = fields.get("summary", "No summary")
    issue_type = fields.get("issuetype", {}).get("name", "Unknown")
    status = fields.get("status", {}).get("name", "Unknown")
    labels = fields.get("labels", [])

    print(f"\n📋 Jira Issue: {key}")
    print(f"   Type: {issue_type}")
    print(f"   Status: {status}")
    print(f"   Summary: {summary}")
    if labels:
        print(f"   Labels: {', '.join(labels)}")


def fetch_and_display_jira_issue(issue_key: str, verbose: bool = False) -> Optional[Dict]:
    """
    Fetch a Jira issue and display its summary.

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
        verbose: Whether to print debug output

    Returns:
        Issue data dictionary or None if fetch failed
    """
    issue_data = fetch_jira_issue(issue_key, verbose)
    if issue_data:
        display_jira_issue_summary(issue_data)
    return issue_data
