"""Azure DevOps CLI commands.

These are action commands that read state from the JSON file and execute.
They are parameterless for easy auto-approval.
"""

import os
import re
import sys
from typing import Any, Dict, Optional

from ...state import (
    get_pull_request_id,
    get_thread_id,
    get_value,
    is_dry_run,
    set_value,
    should_resolve_thread,
)
from ..subprocess_utils import run_safe
from .auth import get_auth_headers, get_pat
from .config import AzureDevOpsConfig
from .helpers import (
    build_thread_context,
    convert_to_pull_request_title,
    format_approval_content,
    get_repository_id,
    parse_bool_from_state_value,
    parse_json_response,
    print_threads,
    require_requests,
    resolve_thread_by_id,
    verify_az_cli,
)
from .pull_request_details_commands import (
    _get_pull_request_iterations,
    get_change_tracking_id_for_file,
)


def _extract_issue_key_from_branch(branch_name: str) -> Optional[str]:
    """
    Extract a Jira issue key from a branch name.

    Searches for patterns like "DFLY-1234" in the branch name.
    Returns the first match found (case-insensitive, returned in uppercase).

    Args:
        branch_name: The branch name to search (e.g., "feature/DFLY-1234/my-feature")

    Returns:
        The extracted issue key (e.g., "DFLY-1234") or None if not found.
    """
    # Match Jira issue key pattern: PROJECT-NUMBER
    # Common patterns: DFLY-1234, ABC-12, PROJECT-99999
    match = re.search(r"([A-Z]{2,10}-\d+)", branch_name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def parse_bool_from_state(key: str, default: bool = False) -> bool:
    """
    Parse a boolean value from state, handling various string representations.

    Args:
        key: The state key to read.
        default: Default value if key is not set.

    Returns:
        Boolean value parsed from state.
    """
    raw_value = get_value(key)
    return parse_bool_from_state_value(raw_value, default)


def require_content() -> str:
    """Get content from state, exiting if not available."""
    content = get_value("content")
    if not content:
        print(
            'Error: No content found. Use: dfly-set content "your message"',
            file=sys.stderr,
        )
        sys.exit(1)
    return content


def reply_to_pull_request_thread() -> None:
    """
    Reply to an existing pull request comment thread.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - thread_id (required): Thread ID to reply to
    - content (required): Reply content (supports multiline)
    - resolve_thread (optional): Whether to resolve after replying
    - dry_run (optional): Preview without making API calls

    Usage:
        dfly-set pull_request_id 23046
        dfly-set thread_id 139474
        dfly-set content "Thanks for the feedback!

        I've made the changes you suggested."
        dfly-reply-to-pull-request-thread
    """
    requests = require_requests()

    # Get required values from state
    pull_request_id = get_pull_request_id(required=True)
    thread_id = get_thread_id(required=True)
    content = require_content()

    resolve_thread_flag = should_resolve_thread()
    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print(f"[DRY RUN] Would reply to thread {thread_id} on PR {pull_request_id}")
        print(f"Content:\n{content}")
        if resolve_thread_flag:
            print("[DRY RUN] Would also resolve the thread")
        return

    # Get auth and repo info
    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    # Add comment to thread
    comment_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads", thread_id, "comments")

    comment_body = {
        "content": content,
        "commentType": "text",
    }

    print(f"Adding reply to thread {thread_id} on PR {pull_request_id}...")
    response = requests.post(comment_url, headers=headers, json=comment_body)
    response.raise_for_status()

    result = response.json()
    print(f"Reply added successfully (comment ID: {result.get('id')})")

    # Optionally resolve thread
    if resolve_thread_flag:
        print(f"Resolving thread {thread_id}...")
        resolve_thread_by_id(
            requests,
            headers,
            config,
            repo_id,
            pull_request_id,
            thread_id,
            status="fixed",
        )
        print(f"Thread {thread_id} resolved")


def add_pull_request_comment() -> None:
    """
    Add a new comment to a pull request.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - content (required): Comment content (supports multiline)
    - path (optional): File path for file-level comment
    - line (optional): Line number for line-level comment
    - end_line (optional): End line for multi-line comment
    - is_pull_request_approval (optional): Whether this is an approval comment (adds sentinel banner)
    - leave_thread_active (optional): Whether to keep thread active (default: resolve after posting)
    - dry_run (optional): Preview without making API calls

    Usage:
        dfly-set pull_request_id 23046
        dfly-set content "Great work on this PR!"
        dfly-add-pull-request-comment

        # For file-level comment
        dfly-set path "src/main.py"
        dfly-set line 42
        dfly-add-pull-request-comment

        # For approval comment
        dfly-set is_pull_request_approval true
        dfly-add-pull-request-comment
    """
    requests = require_requests()

    pull_request_id = get_pull_request_id(required=True)
    content = require_content()

    dry_run = is_dry_run()
    is_approval = parse_bool_from_state("is_pull_request_approval", default=False)
    leave_thread_active = parse_bool_from_state("leave_thread_active", default=False)

    # Apply approval formatting if requested
    if is_approval:
        content = format_approval_content(content)

    # Optional file context
    path = get_value("path")
    line = get_value("line")
    end_line = get_value("end_line")

    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print(f"[DRY RUN] Would add comment to PR {pull_request_id}")
        if path:
            line_info = f", Line: {line}" if line else ""
            end_line_info = f"-{end_line}" if end_line else ""
            print(f"[DRY RUN] File: {path}{line_info}{end_line_info}")
        if is_approval:
            print("[DRY RUN] Comment will include approval sentinel banner")
        if not leave_thread_active:
            print("[DRY RUN] Would also resolve the thread after posting")
        print(f"Content:\n{content}")
        return

    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    # Build thread context for file-level comments
    thread_context = build_thread_context(path, line, end_line)

    # Get latest iteration ID and changeTrackingId for file-level comments
    # to avoid "file no longer exists" issue
    latest_iteration_id = None
    change_tracking_id = None
    if thread_context and path:
        iterations = _get_pull_request_iterations(
            config.organization, config.project, repo_id, pull_request_id, headers
        )
        if iterations:
            latest_iteration_id = max(it.get("id", 0) for it in iterations)
            if latest_iteration_id:
                print(f"Using iteration {latest_iteration_id} for file context")
                # Get the changeTrackingId for this specific file
                change_tracking_id = get_change_tracking_id_for_file(
                    config.organization,
                    config.project,
                    repo_id,
                    pull_request_id,
                    latest_iteration_id,
                    path,
                    headers,
                )
                if change_tracking_id:
                    print(f"Found changeTrackingId {change_tracking_id} for file '{path}'")
                else:
                    print(f"Warning: Could not find changeTrackingId for '{path}'")

    # Create thread with comment
    thread_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")

    thread_body: Dict[str, Any] = {
        "comments": [
            {
                "content": content,
                "commentType": "text",
            }
        ],
        "status": "active",
    }

    if thread_context:
        thread_body["threadContext"] = thread_context
        # Add iteration context so comments are anchored to correct iteration
        if latest_iteration_id and change_tracking_id:
            thread_body["pullRequestThreadContext"] = {
                "iterationContext": {
                    "firstComparingIteration": 1,
                    "secondComparingIteration": latest_iteration_id,
                },
                "changeTrackingId": change_tracking_id,
            }

    print(f"Adding comment to PR {pull_request_id}...")
    response = requests.post(thread_url, headers=headers, json=thread_body)
    response.raise_for_status()

    result = response.json()
    thread_id = result.get("id")
    print(f"Comment added successfully (thread ID: {thread_id})")

    # Optionally resolve thread (default behavior unless leave_thread_active is True)
    if not leave_thread_active and thread_id:
        print(f"Resolving thread {thread_id}...")
        resolve_thread_by_id(
            requests,
            headers,
            config,
            repo_id,
            pull_request_id,
            thread_id,
            status="closed",
        )
        print(f"Thread {thread_id} resolved")


def create_pull_request() -> None:
    """
    Create a pull request from the current branch.

    Reads from state:
    - source_branch (required): Source branch name
    - title (required): PR title (Markdown links will be stripped)
    - description (optional): PR description
    - target_branch (optional): Target branch, defaults to 'main'
    - draft (optional): Whether to create as draft, defaults to True
    - dry_run (optional): Preview without making API calls

    Usage:
        dfly-set source_branch "feature/DFLY-1234/my-feature"
        dfly-set title "feature([DFLY-1234](https://jira.swica.ch/browse/DFLY-1234)): add feature"
        dfly-set description "This PR adds the new feature"
        dfly-create-pull-request
    """
    # Get required values from state
    source_branch = get_value("source_branch")
    if not source_branch:
        print(
            'Error: No source_branch found. Use: dfly-set source_branch "branch-name"',
            file=sys.stderr,
        )
        sys.exit(1)

    title = get_value("title")
    if not title:
        print('Error: No title found. Use: dfly-set title "PR title"', file=sys.stderr)
        sys.exit(1)

    # Strip Markdown links from title
    title = convert_to_pull_request_title(title)

    # Get optional values
    description = get_value("description") or ""
    target_branch = get_value("target_branch") or "main"

    # Draft mode defaults to True (opt-out via draft=false)
    # If draft is explicitly set to false/0/no, then draft=False; otherwise draft=True
    draft_raw = get_value("draft")
    if draft_raw is None:
        draft = True
    elif isinstance(draft_raw, bool):
        draft = draft_raw
    else:
        draft = str(draft_raw).lower() not in ("0", "false", "no")

    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print("[DRY RUN] Would create PR:")
        print(f"  Source Branch: {source_branch}")
        print(f"  Target Branch: {target_branch}")
        print(f"  Title: {title}")
        print(f"  Draft Mode: {draft}")
        if description:
            print(f"  Description: {description}")
        print(f"  Org/Project: {config.organization} / {config.project}")
        print(f"  Repository: {config.repository}")
        return

    # Verify Azure CLI is available
    verify_az_cli()

    # Set PAT for az CLI
    pat = get_pat()
    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Creating pull request for '{source_branch}' -> '{target_branch}'...")

    # Build az repos pr create command
    cmd = [
        "az",
        "repos",
        "pr",
        "create",
        "--source-branch",
        source_branch,
        "--target-branch",
        target_branch,
        "--title",
        title,
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--repository",
        config.repository,
        "--output",
        "json",
    ]

    if draft:
        cmd.append("--draft")

    if description:
        cmd.extend(["--description", description])

    result = run_safe(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error creating PR: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    pr_data = parse_json_response(result.stdout, "PR response")

    pull_request_id = pr_data.get("pullRequestId")
    print("Pull request created successfully.")
    print(f"PR ID: {pull_request_id}")

    # Construct and display the UI URL
    repo_web_url = pr_data.get("repository", {}).get("webUrl", "")
    pr_ui_url = ""
    if repo_web_url:
        pr_ui_url = f"{repo_web_url}/pullrequest/{pull_request_id}"
        print(f"PR URL: {pr_ui_url}")

    # Store the PR ID in state for subsequent commands
    if pull_request_id:
        set_value("pull_request_id", pull_request_id)
        print(f"(PR ID {pull_request_id} saved to state for subsequent commands)")

        # Try to advance workflow if applicable
        try:
            from ..workflows.advancement import try_advance_workflow_after_pr_creation

            try_advance_workflow_after_pr_creation(pull_request_id, pr_ui_url)
        except ImportError:
            pass  # Workflows module not available


def resolve_thread() -> None:
    """
    Resolve (close) a pull request comment thread.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - thread_id (required): Thread ID to resolve
    - dry_run (optional): Preview without making API calls

    Usage:
        dfly-set pull_request_id 23046
        dfly-set thread_id 139474
        dfly-resolve-thread
    """
    requests = require_requests()

    pull_request_id = get_pull_request_id(required=True)
    thread_id = get_thread_id(required=True)
    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print(f"[DRY RUN] Would resolve thread {thread_id} on PR {pull_request_id}")
        print(f"Repository: {config.repository} | Org/Project: {config.organization} / {config.project}")
        return

    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    print(f"Resolving comment thread {thread_id} on PR {pull_request_id}...")
    resolve_thread_by_id(requests, headers, config, repo_id, pull_request_id, thread_id, status="closed")
    print(f"Thread {thread_id} resolved.")


def get_pull_request_threads() -> None:
    """
    Get all comment threads for a pull request.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - dry_run (optional): Preview without making API calls

    Outputs thread information including:
    - Thread ID
    - Status (active, fixed, closed, etc.)
    - File path (if file-level comment)
    - Comments with author and content

    Usage:
        dfly-set pull_request_id 23046
        dfly-get-pull-request-threads
    """
    requests = require_requests()

    pull_request_id = get_pull_request_id(required=True)
    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print(f"[DRY RUN] Would get threads for PR {pull_request_id}")
        print(f"Repository: {config.repository} | Org/Project: {config.organization} / {config.project}")
        return

    pat = get_pat()
    headers = get_auth_headers(pat)

    print(f"Resolving repository ID for '{config.repository}'...")
    repo_id = get_repository_id(config.organization, config.project, config.repository)

    threads_url = config.build_api_url(repo_id, "pullRequests", pull_request_id, "threads")

    print(f"Fetching threads for PR {pull_request_id}...")
    response = requests.get(threads_url, headers=headers)
    response.raise_for_status()

    data = response.json()
    threads = data.get("value", [])

    if not threads:
        print("No comment threads found.")
        return

    print_threads(threads)


def approve_pull_request() -> None:
    """
    Approve a pull request with an approval sentinel comment.

    This is a convenience wrapper around add_pull_request_comment that automatically
    sets is_pull_request_approval=True and formats the content with approval sentinels.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - content (required): Approval comment content
    - dry_run (optional): Preview without making API calls

    The approval sentinel format is:
        --- APPROVED ---

        <your content>

        --- APPROVED ---

    Usage:
        dfly-set pull_request_id 23046
        dfly-set content "LGTM! All acceptance criteria met."
        dfly-approve-pull-request
    """
    # Set approval mode and delegate to add_pull_request_comment
    set_value("is_pull_request_approval", True)
    add_pull_request_comment()


def mark_pull_request_draft() -> None:
    """
    Mark a pull request as draft.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - dry_run (optional): Preview without making API calls

    Usage:
        dfly-set pull_request_id 23046
        dfly-mark-pull-request-draft
    """
    pull_request_id = get_pull_request_id(required=True)
    dry_run = is_dry_run()
    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print(f"[DRY RUN] Would mark PR {pull_request_id} as draft")
        print(f"Org/Project: {config.organization} / {config.project}")
        return

    # Verify Azure CLI is available
    verify_az_cli()

    # Set PAT for az CLI
    pat = get_pat()
    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Marking PR {pull_request_id} as draft...")

    cmd = [
        "az",
        "repos",
        "pr",
        "update",
        "--id",
        str(pull_request_id),
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--draft",
        "true",
        "--output",
        "json",
    ]

    result = run_safe(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error marking PR as draft: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    pr_data = parse_json_response(result.stdout, "PR response")
    print(f"PR {pull_request_id} marked as draft successfully.")

    # Display the PR URL
    repo_web_url = pr_data.get("repository", {}).get("webUrl", "")
    if repo_web_url:
        pull_request_ui_url = f"{repo_web_url}/pullrequest/{pull_request_id}"
        print(f"PR URL: {pull_request_ui_url}")


def publish_pull_request() -> None:
    """
    Publish a pull request (remove draft status) and optionally enable auto-complete.

    Reads from state:
    - pull_request_id (required): Pull request ID
    - skip_auto_complete (optional): If true, don't enable auto-complete (default: false)
    - dry_run (optional): Preview without making API calls

    Usage:
        dfly-set pull_request_id 23046
        dfly-publish-pull-request

        # To skip auto-complete:
        dfly-set skip_auto_complete true
        dfly-publish-pull-request
    """
    pull_request_id = get_pull_request_id(required=True)
    dry_run = is_dry_run()
    skip_auto_complete = parse_bool_from_state("skip_auto_complete", default=False)
    config = AzureDevOpsConfig.from_state()

    if dry_run:
        print(f"[DRY RUN] Would publish PR {pull_request_id}")
        print(f"Org/Project: {config.organization} / {config.project}")
        if skip_auto_complete:
            print("[DRY RUN] Auto-complete: Skipped")
        else:
            print("[DRY RUN] Auto-complete: Will be enabled")
        return

    # Verify Azure CLI is available
    verify_az_cli()

    # Set PAT for az CLI
    pat = get_pat()
    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

    print(f"Publishing PR {pull_request_id}...")

    # Remove draft status
    cmd = [
        "az",
        "repos",
        "pr",
        "update",
        "--id",
        str(pull_request_id),
        "--organization",
        config.organization,
        "--project",
        config.project,
        "--draft",
        "false",
        "--output",
        "json",
    ]

    result = run_safe(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"Error publishing PR: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    pr_data = parse_json_response(result.stdout, "PR response")
    print(f"PR {pull_request_id} published successfully.")

    # Enable auto-complete unless skipped
    if not skip_auto_complete:
        print(f"Setting auto-complete on PR {pull_request_id}...")

        auto_complete_cmd = [
            "az",
            "repos",
            "pr",
            "update",
            "--id",
            str(pull_request_id),
            "--organization",
            config.organization,
            "--project",
            config.project,
            "--auto-complete",
            "true",
            "--output",
            "json",
        ]

        auto_result = run_safe(auto_complete_cmd, capture_output=True, text=True, env=env)

        if auto_result.returncode != 0:
            print(
                "Warning: Failed to set auto-complete. PR is published but auto-complete not enabled.",
                file=sys.stderr,
            )
            print(f"Error: {auto_result.stderr}", file=sys.stderr)
        else:
            print(f"Auto-complete enabled on PR {pull_request_id}.")

    # Display the PR URL
    repo_web_url = pr_data.get("repository", {}).get("webUrl", "")
    if repo_web_url:
        pull_request_ui_url = f"{repo_web_url}/pullrequest/{pull_request_id}"
        print(f"PR URL: {pull_request_ui_url}")
