"""Pull Request Review commands - orchestrates PR review workflow.

This module provides the main entry point for reviewing pull requests,
handling the resolution of PR IDs from Jira issues and vice versa.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set

from ...state import get_state_dir, get_value
from ..subprocess_utils import run_safe
from .auth import get_pat
from .config import AzureDevOpsConfig
from .helpers import verify_az_cli

# Import helper modules


def _get_jira_issue_key_from_state() -> Optional[str]:
    """Get Jira issue key from state."""
    return get_value("jira.issue_key")


def _get_pull_request_id_from_state() -> Optional[int]:
    """Get pull request ID from state."""
    value = get_value("pull_request_id")
    if value is not None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return None


def _get_linked_pull_request_from_jira(issue_key: str) -> Optional[int]:
    """
    Fetch Jira issue and extract linked Azure DevOps pull request ID.

    This looks for remote links that point to Azure DevOps pull requests.

    Args:
        issue_key: Jira issue key (e.g., DFLY-1234)

    Returns:
        Pull request ID if found, None otherwise
    """
    import re

    try:
        import requests as req_module
    except ImportError:
        print("Warning: 'requests' library required for Jira API calls", file=sys.stderr)
        return None

    # Import Jira config
    try:
        from ..jira.config import get_jira_base_url, get_jira_headers
        from ..jira.helpers import _get_ssl_verify
    except ImportError:  # pragma: no cover
        print("Warning: Jira module not available", file=sys.stderr)
        return None

    base_url = get_jira_base_url()
    headers = get_jira_headers()
    ssl_verify = _get_ssl_verify()

    # First, get the issue with remote links
    issue_url = f"{base_url}/rest/api/2/issue/{issue_key}?fields=summary"

    try:
        response = req_module.get(issue_url, headers=headers, verify=ssl_verify, timeout=30)
        if response.status_code != 200:
            return None
    except Exception:
        return None

    # Get remote links for the issue
    remote_links_url = f"{base_url}/rest/api/2/issue/{issue_key}/remotelink"

    try:
        response = req_module.get(remote_links_url, headers=headers, verify=ssl_verify, timeout=30)
        if response.status_code == 200:
            remote_links = response.json()

            # Look for Azure DevOps PR links
            # Pattern: https://dev.azure.com/{org}/{project}/_git/{repo}/pullrequest/{id}
            pr_url_pattern = re.compile(r"pullrequest[s]?/(\d+)", re.IGNORECASE)

            for link in remote_links:
                link_url = link.get("object", {}).get("url", "")
                if "dev.azure.com" in link_url or "visualstudio.com" in link_url:
                    match = pr_url_pattern.search(link_url)
                    if match:
                        return int(match.group(1))
    except Exception:  # pragma: no cover
        pass

    return None


def checkout_and_sync_branch(
    source_branch: str,
    pull_request_id: Optional[int] = None,
    save_files_on_branch: bool = False,
) -> tuple[bool, Optional[str], Set[str]]:
    """
    Checkout the PR source branch, fetch main, and rebase onto it.

    This prepares the local working copy for the review by:
    1. Checking out the source branch
    2. Fetching the latest from origin/main
    3. Rebasing onto main (continues even if conflicts, with warning)

    Args:
        source_branch: The PR source branch name (without refs/heads/)
        pull_request_id: Optional PR ID for saving files_on_branch to JSON
        save_files_on_branch: Whether to save files_on_branch to JSON file

    Returns:
        Tuple of (success, error_message, files_on_branch)
        - success: True if checkout succeeded and we can proceed
        - error_message: If success is False, the message to show the user
        - files_on_branch: Set of file paths changed on this branch vs main
    """
    from ..git.operations import (
        checkout_branch,
        fetch_main,
        get_files_changed_on_branch,
        rebase_onto_main,
    )

    # Step 1: Checkout the source branch
    print(f"\nChecking out PR source branch: {source_branch}...")
    checkout_result = checkout_branch(source_branch)

    if not checkout_result.is_success:
        if checkout_result.needs_user_action:
            return (
                False,
                f"\n{'=' * 60}\n"
                f"⚠️  CANNOT CHECKOUT BRANCH\n"
                f"{'=' * 60}\n\n"
                f"{checkout_result.message}\n\n"
                f"After resolving, restart the workflow with:\n"
                f"  agdt-review-pull-request\n"
                f"{'=' * 60}",
                set(),
            )
        return (  # pragma: no cover
            False,
            f"Error checking out branch: {checkout_result.message}",
            set(),
        )

    # Step 2: Fetch latest from main
    print("\nFetching latest from origin/main...")
    fetch_success = fetch_main()
    if not fetch_success:
        print("Warning: Could not fetch from origin/main, continuing without rebase...")
    else:
        # Step 3: Rebase onto main (continue even on conflicts)
        print("Rebasing onto origin/main...")
        rebase_result = rebase_onto_main()

        if rebase_result.is_success:
            print("Branch is synced with main.")
        elif rebase_result.needs_manual_resolution:
            # Continue with review but warn about conflicts
            print(f"\n{'=' * 60}")
            print("⚠️  REBASE CONFLICTS DETECTED")
            print("=" * 60)
            print("The branch has conflicts with main that should be resolved.")
            print("However, the review can continue with the current branch state.")
            print("After the review, you may want to resolve conflicts separately.")
            print("=" * 60 + "\n")
        else:
            print(f"Warning: {rebase_result.message}")
            print("Continuing with review...")

    # Step 4: Get files changed on this branch vs main
    print("\nIdentifying files changed on this branch...")
    files_on_branch = get_files_changed_on_branch()
    files_set = set(files_on_branch)
    print(f"Found {len(files_set)} file(s) changed on this branch.")

    # Optionally save files_on_branch to JSON for async workflows
    if save_files_on_branch and pull_request_id:
        scripts_dir = Path(__file__).parent.parent.parent.parent.parent
        temp_dir = scripts_dir / "temp"
        prompts_dir = temp_dir / "pull-request-review" / "prompts" / str(pull_request_id)
        prompts_dir.mkdir(parents=True, exist_ok=True)
        files_on_branch_path = prompts_dir / "files-on-branch.json"
        with open(files_on_branch_path, "w", encoding="utf-8") as f:
            json.dump({"files": list(files_set)}, f, indent=2)
        print(f"Saved files on branch to: {files_on_branch_path}")

    return True, None, files_set


def _normalize_path_for_comparison(path: str) -> str:
    """
    Normalize a file path for comparison.

    Strips leading slashes and normalizes to forward slashes.

    Args:
        path: File path to normalize

    Returns:
        Normalized path for comparison
    """
    if not path:
        return ""
    return path.strip().replace("\\", "/").lstrip("/").lower()


def _fetch_pull_request_basic_info(pull_request_id: int, config: AzureDevOpsConfig) -> Optional[Dict[str, Any]]:
    """
    Fetch basic pull request info using az CLI.

    Args:
        pull_request_id: PR ID to fetch
        config: Azure DevOps configuration

    Returns:
        PR data dict or None if failed
    """
    verify_az_cli()
    pat = get_pat()

    env = os.environ.copy()
    env["AZURE_DEVOPS_EXT_PAT"] = pat

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
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _fetch_and_display_jira_issue(issue_key: str) -> bool:
    """
    Fetch and display Jira issue details.

    Args:
        issue_key: Jira issue key

    Returns:
        True if successful, False otherwise
    """
    try:
        from ..jira.get_commands import get_issue
        from ..jira.state_helpers import set_jira_value

        # Set the issue key in state
        set_jira_value("issue_key", issue_key)

        # Call get_issue (this prints details and saves to temp file)
        get_issue()
        return True
    except SystemExit:
        # get_issue calls sys.exit(1) on failure - catch and continue
        print(
            f"Warning: Jira issue {issue_key} could not be fetched. Proceeding with PR review only.",
            file=sys.stderr,
        )
        return False
    except Exception as e:
        print(f"Warning: Failed to fetch Jira issue {issue_key}: {e}", file=sys.stderr)
        return False


def generate_review_prompts(
    pull_request_id: int,
    pr_details: Optional[Dict] = None,
    include_reviewed: bool = False,
    files_on_branch: Optional[Set[str]] = None,
) -> tuple[int, int, int, Path]:
    """
    Generate file review prompts from PR details.

    This function creates the queue.json manifest and individual file prompts
    for the PR review workflow.

    Args:
        pull_request_id: PR ID
        pr_details: Full PR details payload. If None, loads from temp file.
        include_reviewed: Whether to include already-reviewed files
        files_on_branch: Set of file paths that are actually changed on the branch.
            If None and files-on-branch.json exists, loads from that file.
            If provided, files not in this set will be filtered out (they likely
            came from recently merged PRs).

    Returns:
        Tuple of (prompts_generated, skipped_reviewed_count, skipped_not_on_branch_count, prompts_directory)
    """
    from datetime import datetime, timezone

    from .review_helpers import (
        build_reviewed_paths_set,
        filter_threads,
        get_threads_for_file,
        normalize_repo_path,
    )

    scripts_dir = Path(__file__).parent.parent.parent.parent.parent  # Up to scripts/
    temp_dir = scripts_dir / "temp"
    prompts_dir = temp_dir / "pull-request-review" / "prompts" / str(pull_request_id)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Load pr_details from temp file if not provided
    if pr_details is None:
        details_path = temp_dir / "temp-get-pull-request-details-response.json"
        if not details_path.exists():
            raise FileNotFoundError(f"PR details file not found: {details_path}. Run get_pull_request_details first.")
        with open(details_path, encoding="utf-8") as f:
            pr_details = json.load(f)

    # Load files_on_branch from JSON if not provided
    if files_on_branch is None:
        files_on_branch_path = prompts_dir / "files-on-branch.json"
        if files_on_branch_path.exists():
            with open(files_on_branch_path, encoding="utf-8") as f:
                files_data = json.load(f)
                files_on_branch = set(files_data.get("files", []))
                print(f"Loaded {len(files_on_branch)} files from files-on-branch.json")

    files_payload = pr_details.get("files", [])
    threads_payload = filter_threads(pr_details.get("threads", []))

    # Build set of reviewed files
    reviewed_paths = set()
    if not include_reviewed:
        reviewed_paths = build_reviewed_paths_set(pr_details)

    # Normalize files_on_branch for comparison
    normalized_branch_files: Set[str] | None = None
    if files_on_branch is not None:
        normalized_branch_files = {_normalize_path_for_comparison(f) for f in files_on_branch}

    # Save snapshots
    files_snapshot_path = prompts_dir / "pull-request-files.json"
    with open(files_snapshot_path, "w", encoding="utf-8") as f:
        json.dump({"files": files_payload}, f, indent=2)

    threads_snapshot_path = prompts_dir / "pull-request-threads.json"
    with open(threads_snapshot_path, "w", encoding="utf-8") as f:
        json.dump({"threads": threads_payload}, f, indent=2)

    # Copy Jira issue if available
    state_dir = get_state_dir()
    jira_temp_path = state_dir / "temp-get-issue-details-response.json"
    jira_prompt_path = prompts_dir / "pull-request-jira-issue.json"
    if jira_temp_path.exists():  # pragma: no cover
        jira_prompt_path.write_text(jira_temp_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        jira_prompt_path.write_text("{}", encoding="utf-8")

    # Generate prompts for each file
    prompts_generated = 0
    skipped_reviewed_count = 0
    skipped_not_on_branch_count = 0
    queue_entries = []

    for file_detail in files_payload:
        file_path = file_detail.get("path", "")
        normalized_path = normalize_repo_path(file_path)

        # Skip files already reviewed
        if not include_reviewed and normalized_path and normalized_path.lower() in reviewed_paths:
            print(f"Skipping already reviewed file: {file_path}")
            skipped_reviewed_count += 1
            continue

        # Skip files not actually on the branch (from recently merged PRs)
        if normalized_branch_files is not None:
            normalized_for_comparison = _normalize_path_for_comparison(file_path)
            if normalized_for_comparison not in normalized_branch_files:
                print(f"Skipping file not on branch (likely from merged PR): {file_path}")
                skipped_not_on_branch_count += 1
                continue

        threads_for_file = get_threads_for_file(threads_payload, file_path)
        prompt_path = _write_file_prompt(prompts_dir, file_detail, threads_for_file)
        prompts_generated += 1

        queue_entries.append(
            {
                "path": file_path,
                "normalizedPath": normalized_path or normalize_repo_path(file_path),
                "promptFile": prompt_path.name,
                "promptPath": str(prompt_path),
                "status": "pending",
            }
        )

    # Write queue manifest
    queue_payload = {
        "pullRequestId": pull_request_id,
        "generatedUtc": datetime.now(timezone.utc).isoformat(),
        "total": prompts_generated,
        "pending": queue_entries,
        "completed": [],
    }

    queue_path = prompts_dir / "queue.json"
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue_payload, f, indent=2)

    return prompts_generated, skipped_reviewed_count, skipped_not_on_branch_count, prompts_dir


def _write_file_prompt(directory: Path, file_detail: Dict, threads_for_file: list) -> Path:
    """Write a file review prompt to disk."""
    from .review_helpers import convert_to_prompt_filename

    filename = convert_to_prompt_filename(file_detail.get("path", ""))
    prompt_path = directory / filename

    file_json = json.dumps(file_detail, indent=2, ensure_ascii=False)
    threads_json = json.dumps(threads_for_file, indent=2, ensure_ascii=False) if threads_for_file else "[]"

    lines = [
        f"# File Review: {file_detail.get('path', 'unknown')}",
        "",
        "## File Diff Object",
        "",
        "```json",
        file_json,
        "```",
        "",
        "## Existing Threads",
        "",
        "```json",
        threads_json,
        "```",
    ]

    prompt_path.write_text("\n".join(lines), encoding="utf-8")
    return prompt_path


def print_review_instructions(
    pull_request_id: int,
    prompts_dir: Path,
    prompts_generated: int,
    skipped_reviewed_count: int,
    skipped_not_on_branch_count: int = 0,
) -> None:
    """Print instructions for the AI agent to follow."""
    print("")
    print("=" * 60)
    print("PULL REQUEST REVIEW WORKFLOW")
    print("=" * 60)
    print("")
    print(f"PR ID: {pull_request_id}")
    print(f"Prompts generated: {prompts_generated}")
    print(f"Skipped (already reviewed): {skipped_reviewed_count}")
    if skipped_not_on_branch_count > 0:
        print(f"Skipped (not on branch, from merged PRs): {skipped_not_on_branch_count}")
    print(f"Prompts directory: {prompts_dir}")
    print("")
    print("=" * 60)
    print("SHARED CONTEXT FOR THIS REVIEW")
    print("=" * 60)
    print("")
    print("Review snapshots are saved in the prompts folder:")
    print("  • pull-request-files.json - All files in the PR diff")
    print("  • pull-request-threads.json - Existing comment threads")
    print("  • pull-request-jira-issue.json - Linked Jira issue details")
    print("")
    print("Keep analysis scoped to one file at a time; use shared artifacts for background context.")
    print("")
    print("=" * 60)
    print("CONSOLE CHECKLIST (for each file)")
    print("=" * 60)
    print("")
    print("1. Open the file prompt and analyze the diff + any existing threads.")
    print("2. Verify repository conventions/invariants for that file and capture concrete feedback.")
    print("3. Post the review with the appropriate command; let the queue advance automatically.")
    print("")
    print("=" * 60)
    print("REVIEW COMMANDS")
    print("=" * 60)
    print("")
    print("Set the file path and content first:")
    print(f"  agdt-set pull_request_id {pull_request_id}")
    print('  agdt-set file_review.file_path "/path/to/file.ts"')
    print('  agdt-set content "Your review comment here"')
    print("")
    print("Then use one of these commands:")
    print("")
    print("• APPROVE (no issues found):")
    print("    agdt-approve-file")
    print("")
    print("• REQUEST CHANGES (with optional line numbers):")
    print("    agdt-set line 42")
    print("    agdt-set end_line 45  # optional, for multi-line context")
    print("    agdt-request-changes")
    print("")
    print("• REQUEST CHANGES WITH CODE SUGGESTION:")
    print("    agdt-set line 42")
    print('    agdt-set content "```suggestion')
    print("    // Your suggested code here")
    print('    ```"')
    print("    agdt-request-changes-with-suggestion")
    print("")
    print("=" * 60)
    print("IMPORTANT NOTES")
    print("=" * 60)
    print("")
    print("• After reviewing the final file, the overarching PR comments will be")
    print("  generated automatically. This may take up to 30 seconds.")
    print("• DO NOT RUN ANY COMMANDS after submitting the final file review!")
    print("  Wait for the process to complete.")
    print("• After all files are reviewed, provide a summary of your findings.")
    print("")

    if prompts_generated == 0:
        print("WARNING: No prompts were generated. All files may already be reviewed.")
        print("Use include_reviewed=True to re-review files if needed.")
    else:
        print("Ready to begin review. Process the queue starting with the first pending file.")


def setup_pull_request_review() -> None:
    """
    Set up a pull request review workflow (used by initiate_pull_request_review_workflow).

    This is a streamlined version of review_pull_request that assumes the PR ID
    is already resolved and set in state. It performs the following steps:
    1. Fetch PR details via get_pull_request_details
    2. Optionally fetch Jira issue details
    3. Checkout source branch and sync with main
    4. Generate review prompts and queue.json
    5. Print review instructions
    6. Initialize workflow state

    State keys:
        pull_request_id (required): PR ID
        jira.issue_key (optional): Jira issue key
        include_reviewed (optional): Whether to include already-reviewed files

    This function is designed to be called in a background task from the
    workflow initiation command.
    """
    from .pull_request_details_commands import get_pull_request_details

    # Read parameters from state
    pr_id_str = get_value("pull_request_id")
    if not pr_id_str:
        print("ERROR: pull_request_id is required in state.", file=sys.stderr)
        sys.exit(1)
    pull_request_id = int(pr_id_str)

    jira_issue_key = get_value("jira.issue_key")
    include_reviewed = str(get_value("include_reviewed", "")).lower() in ("true", "1", "yes")

    # Step 1: Fetch Jira issue details if we have a key
    if jira_issue_key:
        print(f"\nFetching Jira issue details for {jira_issue_key}...")
        _fetch_and_display_jira_issue(jira_issue_key)

    # Step 2: Fetch PR details
    print(f"\nFetching pull request details for PR {pull_request_id}...")
    get_pull_request_details()

    # Step 3: Load the PR details from the temp file
    scripts_dir = Path(__file__).parent.parent.parent.parent.parent
    temp_dir = scripts_dir / "temp"
    details_path = temp_dir / "temp-get-pull-request-details-response.json"

    if not details_path.exists():
        print("ERROR: PR details file not found after fetch.", file=sys.stderr)
        sys.exit(1)

    with open(details_path, encoding="utf-8") as f:
        pr_details = json.load(f)

    # Step 4: Checkout source branch and sync with main
    pr_info = pr_details.get("pullRequest", pr_details)
    source_branch = pr_info.get("sourceRefName", "").replace("refs/heads/", "")

    files_on_branch: Set[str] | None = None
    if source_branch:
        print(f"\nChecking out source branch '{source_branch}' and syncing with main...")
        checkout_success, checkout_error, files_on_branch = checkout_and_sync_branch(
            source_branch, pull_request_id, save_files_on_branch=True
        )

        if not checkout_success:
            print("", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("BRANCH CHECKOUT/SYNC ISSUE", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("", file=sys.stderr)
            print(f"Error: {checkout_error}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Please resolve this issue and re-run the workflow.", file=sys.stderr)
            print("", file=sys.stderr)
            sys.exit(1)
    else:
        print("Warning: Could not determine source branch from PR details", file=sys.stderr)

    # Step 5: Generate review prompts
    print("\nGenerating file review prompts...")
    prompts_generated, skipped_reviewed_count, skipped_not_on_branch_count, prompts_dir = generate_review_prompts(
        pull_request_id,
        pr_details,
        include_reviewed,
        files_on_branch,
    )

    # Step 6: Print instructions
    print_review_instructions(
        pull_request_id, prompts_dir, prompts_generated, skipped_reviewed_count, skipped_not_on_branch_count
    )

    # Step 7: Initialize workflow with PR context
    try:
        from ...prompts.loader import load_and_render_prompt
        from ...state import set_workflow_state

        pr_title = pr_info.get("title", "")
        pr_author = pr_info.get("createdBy", {}).get("displayName", "")
        target_branch = pr_info.get("targetRefName", "").replace("refs/heads/", "")
        file_count = prompts_generated

        workflow_context = {
            "pull_request_id": pull_request_id,
            "jira_issue_key": jira_issue_key or "",
            "pr_title": pr_title,
            "pr_author": pr_author,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "file_count": file_count,
        }

        set_workflow_state(
            name="pull-request-review",
            status="initiated",
            step="initiate",
            context=workflow_context,
        )

        print("\n" + "=" * 60)
        print("WORKFLOW INITIALIZED: pull-request-review")
        print("=" * 60)

        variables = {
            "pull_request_id": pull_request_id,
            "jira_issue_key": jira_issue_key or "",
            "pr_title": pr_title,
            "pr_author": pr_author,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "file_count": file_count,
        }

        load_and_render_prompt(
            workflow_name="pull-request-review",
            step_name="initiate",
            variables=variables,
            save_to_temp=True,
            log_output=True,
        )

    except ImportError:  # pragma: no cover
        pass  # Workflows module not available
    except Exception as e:  # pragma: no cover
        print(f"Warning: Could not initialize workflow: {e}", file=sys.stderr)
