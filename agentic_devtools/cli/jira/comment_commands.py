"""
Jira comment commands: add_comment.
"""

import argparse
import sys

from agentic_devtools.state import is_dry_run, set_value
from agentic_devtools.tools.jira import JiraConfig
from agentic_devtools.tools.jira import add_comment as _tools_add_comment

from .config import get_jira_base_url, get_jira_headers
from .helpers import _get_requests, _get_ssl_verify
from .state_helpers import get_jira_value
from .vpn_wrapper import with_jira_vpn_context


@with_jira_vpn_context
def add_comment(comment: str | None = None, issue_key: str | None = None) -> None:
    """
    Add a comment to an existing Jira issue.

    Args:
        comment: Comment content (overrides state)
        issue_key: Issue key to comment on (overrides state)

    State keys (prefixed with 'jira.'):
    - jira.issue_key: Issue key (used if issue_key not provided)
    - jira.comment: Comment content (used if comment not provided)
    - jira.dry_run: Preview without posting

    After posting, refreshes issue details to update cached state.

    Usage:
        agdt-add-jira-comment --jira-comment "This is my comment"
        agdt-add-jira-comment --jira-issue-key DFLY-1234 --jira-comment "Comment"

        # Or using state:
        agdt-set jira.issue_key DFLY-1234
        agdt-set jira.comment "This is my comment"
        agdt-add-jira-comment
    """
    # Import here to avoid circular dependency
    from .get_commands import get_issue

    # Use parameter if provided, otherwise fall back to state
    resolved_issue_key = issue_key or get_jira_value("issue_key")
    resolved_comment = comment or get_jira_value("comment")
    dry_run = is_dry_run() or get_jira_value("dry_run")

    if not resolved_issue_key:
        print(
            "Error: jira.issue_key is required. Use: agdt-add-jira-comment --jira-issue-key DFLY-1234",
            file=sys.stderr,
        )
        sys.exit(1)
    if not resolved_comment:
        print(
            'Error: jira.comment is required. Use: agdt-add-jira-comment --jira-comment "Your comment"',
            file=sys.stderr,
        )
        sys.exit(1)

    # Update state if parameters were provided (for consistency)
    if issue_key:
        set_value("jira.issue_key", issue_key)
    if comment:
        set_value("jira.comment", comment)

    if dry_run:
        print(f"[DRY RUN] Would add comment to {resolved_issue_key}")
        print(f"Content:\n{resolved_comment}")
        return

    print(f"Adding comment to {resolved_issue_key}...")

    try:
        config = JiraConfig(
            base_url=get_jira_base_url(),
            headers=get_jira_headers(),
            ssl_verify=_get_ssl_verify(),
            requests_module=_get_requests(),
        )
        result = _tools_add_comment(config=config, issue_key=resolved_issue_key, comment=resolved_comment)
        print(f"Comment added successfully (ID: {result['comment_id']})")

        # Refresh issue details to update cached state (matches PowerShell behavior)
        print("Refreshing issue details...")
        get_issue()

        # Try to advance workflow if applicable
        try:
            from ..workflows.advancement import try_advance_workflow_after_jira_comment

            try_advance_workflow_after_jira_comment()
        except ImportError:  # pragma: no cover
            pass  # Workflows module not available

    except Exception as e:
        print(f"Error adding comment: {e}", file=sys.stderr)
        sys.exit(1)


def add_comment_cli() -> None:  # pragma: no cover
    """CLI entry point for add_comment with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Add a comment to a Jira issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-add-jira-comment --jira-comment "This is my comment"
  agdt-add-jira-comment --jira-issue-key DFLY-1234 --jira-comment "Comment"
  # Or using state:
  agdt-set jira.issue_key DFLY-1234
  agdt-set jira.comment "This is my comment"
  agdt-add-jira-comment
        """,
    )

    parser.add_argument(
        "--jira-comment",
        "-c",
        type=str,
        default=None,
        help="Comment content to add (falls back to jira.comment state)",
    )
    parser.add_argument(
        "--jira-issue-key",
        "-k",
        type=str,
        default=None,
        help="Issue key to comment on (falls back to jira.issue_key state)",
    )

    args = parser.parse_args()

    add_comment(comment=args.jira_comment, issue_key=args.jira_issue_key)
