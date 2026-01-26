"""
Jira update commands: update_issue.

Provides the dfly-update-jira-issue command for updating issue fields.
"""

import json
import sys
from typing import Any, Optional

from agentic_devtools.state import is_dry_run

from .config import get_jira_base_url, get_jira_headers
from .helpers import _get_requests, _get_ssl_verify, _parse_comma_separated
from .state_helpers import get_jira_value
from .vpn_wrapper import with_jira_vpn_context


def _build_update_payload(
    summary: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[list[str]] = None,
    labels_add: Optional[list[str]] = None,
    labels_remove: Optional[list[str]] = None,
    assignee: Optional[str] = None,
    priority: Optional[str] = None,
    custom_fields: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Build the payload for updating a Jira issue.

    The Jira API expects:
    - For simple fields: {"fields": {"fieldname": "value"}}
    - For labels with add/remove: {"update": {"labels": [{"add": "label"}, {"remove": "label"}]}}
    """
    payload: dict[str, Any] = {}
    fields: dict[str, Any] = {}
    update: dict[str, Any] = {}

    # Simple field updates
    if summary is not None:
        fields["summary"] = summary

    if description is not None:
        fields["description"] = description

    if assignee is not None:
        # Empty string means unassign
        fields["assignee"] = {"name": assignee} if assignee else None

    if priority is not None:
        fields["priority"] = {"name": priority}

    # Labels handling
    if labels is not None:
        # Replace all labels
        fields["labels"] = labels
    elif labels_add or labels_remove:
        # Incremental label changes
        label_ops = []
        if labels_add:
            for label in labels_add:
                label_ops.append({"add": label})
        if labels_remove:
            for label in labels_remove:
                label_ops.append({"remove": label})
        if label_ops:
            update["labels"] = label_ops

    # Custom fields
    if custom_fields:
        for field_id, value in custom_fields.items():
            fields[field_id] = value

    # Build final payload
    if fields:
        payload["fields"] = fields
    if update:
        payload["update"] = update

    return payload


@with_jira_vpn_context
def update_issue() -> None:
    """
    Update fields on an existing Jira issue.

    Reads from state (all keys prefixed with 'jira.'):
    - jira.issue_key (required): Issue key to update
    - jira.summary (optional): New summary
    - jira.description (optional): New description
    - jira.labels (optional): Comma-separated labels (replaces existing)
    - jira.labels_add (optional): Comma-separated labels to add
    - jira.labels_remove (optional): Comma-separated labels to remove
    - jira.assignee (optional): Username to assign (empty string to unassign)
    - jira.priority (optional): Priority name (e.g., "High", "Medium", "Low")
    - jira.custom_fields (optional): JSON object of custom field IDs to values
    - jira.dry_run (optional): Preview without updating

    At least one field to update must be specified.

    After updating, refreshes issue details to update cached state.

    Usage:
        dfly-set jira.issue_key DFLY-1234
        dfly-set jira.summary "Updated Summary"
        dfly-update-jira-issue

        # Or update labels incrementally:
        dfly-set jira.issue_key DFLY-1234
        dfly-set jira.labels_add "in-progress,needs-review"
        dfly-update-jira-issue
    """
    # Import here to avoid circular dependency
    from .get_commands import get_issue

    requests = _get_requests()

    issue_key = get_jira_value("issue_key")
    dry_run = is_dry_run() or get_jira_value("dry_run")

    if not issue_key:
        print(
            "Error: jira.issue_key is required. Use: dfly-set jira.issue_key DFLY-1234",
            file=sys.stderr,
        )
        sys.exit(1)

    # Gather all possible update fields
    summary = get_jira_value("summary")
    description = get_jira_value("description")
    labels_str = get_jira_value("labels")
    labels_add_str = get_jira_value("labels_add")
    labels_remove_str = get_jira_value("labels_remove")
    assignee = get_jira_value("assignee")
    priority = get_jira_value("priority")
    custom_fields_str = get_jira_value("custom_fields")

    # Parse labels
    labels = _parse_comma_separated(labels_str) if labels_str else None
    labels_add = _parse_comma_separated(labels_add_str) if labels_add_str else None
    labels_remove = _parse_comma_separated(labels_remove_str) if labels_remove_str else None

    # Parse custom fields JSON
    custom_fields = None
    if custom_fields_str:
        try:
            custom_fields = json.loads(custom_fields_str)
            if not isinstance(custom_fields, dict):
                print("Error: jira.custom_fields must be a JSON object", file=sys.stderr)
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in jira.custom_fields: {e}", file=sys.stderr)
            sys.exit(1)

    # Build payload
    payload = _build_update_payload(
        summary=summary,
        description=description,
        labels=labels,
        labels_add=labels_add,
        labels_remove=labels_remove,
        assignee=assignee,
        priority=priority,
        custom_fields=custom_fields,
    )

    if not payload:
        print("Error: No fields to update. Specify at least one of:", file=sys.stderr)
        print("  - jira.summary", file=sys.stderr)
        print("  - jira.description", file=sys.stderr)
        print("  - jira.labels (or jira.labels_add / jira.labels_remove)", file=sys.stderr)
        print("  - jira.assignee", file=sys.stderr)
        print("  - jira.priority", file=sys.stderr)
        print("  - jira.custom_fields", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"[DRY RUN] Would update {issue_key} with:")
        print(json.dumps(payload, indent=2))
        return

    base_url = get_jira_base_url()
    url = f"{base_url}/rest/api/2/issue/{issue_key}"
    headers = get_jira_headers()

    print(f"Updating {issue_key}...")

    try:
        response = requests.put(url, headers=headers, json=payload, verify=_get_ssl_verify())
        response.raise_for_status()

        # Jira returns 204 No Content on success
        print(f"Issue {issue_key} updated successfully")

        # List what was updated
        if "fields" in payload:
            updated_fields = list(payload["fields"].keys())
            print(f"Updated fields: {', '.join(updated_fields)}")
        if "update" in payload:
            updated_ops = list(payload["update"].keys())
            print(f"Updated via operations: {', '.join(updated_ops)}")

        # Refresh issue details to update cached state
        print("Refreshing issue details...")
        get_issue()

    except Exception as e:
        error_msg = str(e)
        # Try to extract more details from response
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                if "errorMessages" in error_detail:
                    error_msg = "; ".join(error_detail["errorMessages"])
                elif "errors" in error_detail:
                    error_msg = json.dumps(error_detail["errors"])
            except (ValueError, AttributeError):
                pass
        print(f"Error updating issue: {error_msg}", file=sys.stderr)
        sys.exit(1)
