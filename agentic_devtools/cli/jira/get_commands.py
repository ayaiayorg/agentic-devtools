"""
Jira get commands: get_issue.
"""

import json
import sys
from datetime import datetime, timezone

from agentic_devtools.state import get_state_dir

from .adf import _convert_adf_to_text
from .config import get_jira_base_url, get_jira_headers
from .helpers import _get_requests, _get_ssl_verify
from .state_helpers import get_jira_value, set_jira_value
from .vpn_wrapper import with_jira_vpn_context


def _fetch_remote_links(requests, base_url: str, issue_key: str, headers: dict) -> list[dict]:
    """Fetch remote links (including PRs) for an issue."""
    url = f"{base_url}/rest/api/2/issue/{issue_key}/remotelink"
    try:
        response = requests.get(url, headers=headers, verify=_get_ssl_verify(), timeout=30)
        response.raise_for_status()
        result = response.json()
        # Ensure we return a list (API returns array of remote links)
        return result if isinstance(result, list) else []
    except Exception:
        # Remote links API may fail silently - not critical
        return []


def _fetch_parent_issue(requests, base_url: str, parent_key: str, headers: dict) -> dict | None:
    """
    Fetch parent issue details for a subtask.

    Args:
        requests: The requests module to use
        base_url: Jira base URL
        parent_key: The parent issue key
        headers: Authentication headers

    Returns:
        Parent issue JSON dict, or None if fetch fails
    """
    fields = "summary,description,comment,labels,issuetype,parent,customfield_10008"
    url = f"{base_url}/rest/api/2/issue/{parent_key}?fields={fields}&comment.maxResults=50"
    try:
        response = requests.get(url, headers=headers, verify=_get_ssl_verify(), timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch parent issue {parent_key}: {e}", file=sys.stderr)
        return None


def _fetch_epic(requests, base_url: str, epic_key: str, headers: dict) -> dict | None:
    """
    Fetch epic issue details for an issue linked to an epic.

    Args:
        requests: The requests module to use
        base_url: Jira base URL
        epic_key: The epic issue key
        headers: Authentication headers

    Returns:
        Epic issue JSON dict, or None if fetch fails
    """
    fields = "summary,description,comment,labels,issuetype,customfield_10008"
    url = f"{base_url}/rest/api/2/issue/{epic_key}?fields={fields}&comment.maxResults=50"
    try:
        response = requests.get(url, headers=headers, verify=_get_ssl_verify(), timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Could not fetch epic {epic_key}: {e}", file=sys.stderr)
        return None


@with_jira_vpn_context
def get_issue() -> None:
    """
    Get details of a Jira issue.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.issue_key (required): Issue key to retrieve

    Outputs:
    - Saves full JSON response to scripts/temp/temp-get-issue-details-response.json
    - If issue is a subtask, also saves parent issue to temp-get-parent-issue-details-response.json
    - If issue has an epic link, also saves epic to temp-get-epic-details-response.json
    - Prints formatted issue details to console

    Features:
    - Automatic subtask detection: checks issuetype.subtask field
    - Automatic parent retrieval: extracts parent key from fields.parent.key
    - Automatic epic retrieval: extracts epic key from customfield_10008
    - No manual configuration needed for parent issues or epics

    State storage:
    - Stores metadata references (file paths, timestamps) instead of full JSON
    - jira.issue_details: {location, retrievalTimestamp}
    - jira.parent_issue_details: {location, key, retrievalTimestamp} (if subtask)
    - jira.epic_details: {location, key, retrievalTimestamp} (if epic linked)

    Usage:
        agdt-set jira.issue_key DFLY-1234
        agdt-get-jira-issue
    """
    requests = _get_requests()

    issue_key = get_jira_value("issue_key")

    if not issue_key:
        print(
            "Error: jira.issue_key is required. Use: agdt-set jira.issue_key DFLY-1234",
            file=sys.stderr,
        )
        sys.exit(1)

    base_url = get_jira_base_url()
    # Include parent field for subtask detection and customfield_10008 for epic link
    fields_param = "summary,description,comment,labels,issuetype,parent,customfield_10008"
    url = f"{base_url}/rest/api/2/issue/{issue_key}?fields={fields_param}&comment.maxResults=50"
    headers = get_jira_headers()

    print(f"Fetching {issue_key}...")

    try:
        response = requests.get(url, headers=headers, verify=_get_ssl_verify(), timeout=30)
        response.raise_for_status()

        issue = response.json()
        fields = issue.get("fields", {})
        retrieval_timestamp = datetime.now(timezone.utc).isoformat()

        # Save JSON response to temp file (matching PowerShell behavior)
        state_dir = get_state_dir()
        response_file = state_dir / "temp-get-issue-details-response.json"
        response_file.write_text(json.dumps(issue, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Issue details saved to: {response_file}")

        # Store metadata reference in state (not the full JSON)
        set_jira_value("issue_details", {"location": str(response_file), "retrievalTimestamp": retrieval_timestamp})

        # Automatic subtask parent detection and retrieval
        issuetype = fields.get("issuetype", {})
        is_subtask = issuetype.get("subtask", False)
        is_epic = issuetype.get("name", "").lower() == "epic"
        parent_issue = None
        epic_issue = None

        if is_subtask:
            parent_data = fields.get("parent", {})
            parent_key = parent_data.get("key")
            if parent_key:
                print(f"\nDetected subtask of {parent_key}, fetching parent issue...")
                parent_issue = _fetch_parent_issue(requests, base_url, parent_key, headers)
                if parent_issue:
                    parent_file = state_dir / "temp-get-parent-issue-details-response.json"
                    parent_file.write_text(json.dumps(parent_issue, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"Parent issue details saved to: {parent_file}")
                    # Store metadata reference for parent (not full JSON)
                    set_jira_value(
                        "parent_issue_details",
                        {"location": str(parent_file), "key": parent_key, "retrievalTimestamp": retrieval_timestamp},
                    )

        # Epic link detection and retrieval (skip for subtasks and epics themselves)
        epic_link = fields.get("customfield_10008")
        if epic_link and not is_subtask and not is_epic:
            print(f"\nDetected epic link {epic_link}, fetching epic...")
            epic_issue = _fetch_epic(requests, base_url, epic_link, headers)
            if epic_issue:
                epic_file = state_dir / "temp-get-epic-details-response.json"
                epic_file.write_text(json.dumps(epic_issue, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"Epic details saved to: {epic_file}")
                # Store metadata reference for epic (not full JSON)
                set_jira_value(
                    "epic_details",
                    {"location": str(epic_file), "key": epic_link, "retrievalTimestamp": retrieval_timestamp},
                )

        # Print formatted output
        print(f"\nKey: {issue.get('key', issue_key)}")
        print(f"Summary: {fields.get('summary')}")
        print(f"Issue Type: {issuetype.get('name', 'none')}")
        if is_subtask and parent_issue:
            parent_fields = parent_issue.get("fields", {})
            parent_key = parent_issue.get("key", "")
            parent_summary = parent_fields.get("summary", "")
            print(f"Parent Issue: {parent_key} - {parent_summary}")
        if epic_issue:
            epic_fields = epic_issue.get("fields", {})
            epic_key = epic_issue.get("key", "")
            epic_summary = epic_fields.get("summary", "")
            print(f"Epic: {epic_key} - {epic_summary}")
        elif epic_link and not is_subtask and not is_epic:
            # Epic link exists but fetch failed
            print(f"Epic: {epic_link} (fetch failed)")
        labels = fields.get("labels", [])
        print(f"Labels: {', '.join(labels) if labels else 'none'}")

        # Print description
        description = fields.get("description", "")
        print("Description:")
        if description:
            # Handle both string and Atlassian Document Format
            if isinstance(description, str):
                print(description)
            elif isinstance(description, dict):
                print(_convert_adf_to_text(description))
            else:
                print(str(description))
        else:
            print("No description")

        # Print comments
        comment_data = fields.get("comment", {})
        comments = comment_data.get("comments", []) if isinstance(comment_data, dict) else []

        if comments:
            print("\nComments (most recent first):")
            # Sort by created date descending
            sorted_comments = sorted(comments, key=lambda c: c.get("created", ""), reverse=True)
            for idx, comment in enumerate(sorted_comments, 1):
                author = comment.get("author", {})
                author_name = author.get("displayName") or author.get("name", "Unknown")
                created = comment.get("created", "")
                comment_id = comment.get("id", "")
                body = comment.get("body", "")

                print(f"[{idx}] {comment_id} by {author_name} @ {created}")
                if isinstance(body, str):
                    print(body)
                elif isinstance(body, dict):
                    print(_convert_adf_to_text(body))
                print("---")
        else:
            print("\nComments: none")

        # Fetch and print remote links (PRs)
        remote_links = _fetch_remote_links(requests, base_url, issue_key, headers)
        pr_links = [
            link
            for link in remote_links
            if "pullrequest" in link.get("object", {}).get("icon", {}).get("url16x16", "").lower()
            or "pull request" in link.get("object", {}).get("title", "").lower()
            or "/pullrequest/" in link.get("object", {}).get("url", "").lower()
        ]

        if pr_links:
            print("\nLinked Pull Requests:")
            for link in pr_links:
                obj = link.get("object", {})
                title = obj.get("title", "Untitled PR")
                url = obj.get("url", "")
                status = obj.get("status", {}).get("resolved", False)
                status_text = "(merged)" if status else "(open)"
                print(f"  • {title} {status_text}")
                if url:
                    print(f"    {url}")
        else:
            # Check for any remote links that might be PRs
            if remote_links:
                print("\nLinked Items:")
                for link in remote_links:
                    obj = link.get("object", {})
                    title = obj.get("title", "Untitled")
                    url = obj.get("url", "")
                    print(f"  • {title}")
                    if url:
                        print(f"    {url}")
            else:
                print("\nLinked Pull Requests: none")

        # Notify workflow manager of the event
        try:
            from ..workflows.advancement import try_advance_workflow_after_jira_issue_retrieved

            try_advance_workflow_after_jira_issue_retrieved(issue_data=issue)
        except ImportError:  # pragma: no cover
            pass  # Workflows module not available

    except Exception as e:
        print(f"Error fetching issue: {e}", file=sys.stderr)
        sys.exit(1)
