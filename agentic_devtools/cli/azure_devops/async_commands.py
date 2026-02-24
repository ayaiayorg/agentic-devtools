"""
Async Azure DevOps command wrappers.

Provides async versions of Azure DevOps commands that run in background processes.
All commands that make HTTP requests to Azure DevOps should have async versions here.

These async commands call the sync functions directly via run_function_in_background,
not via CLI entry points.
"""

import argparse
import sys
from typing import Optional

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.state import get_value, set_value
from agentic_devtools.task_state import print_task_tracking_info


def _set_value_if_provided(key: str, value: Optional[str]) -> None:
    """Set a state value if provided (not None)."""
    if value is not None:
        set_value(key, value)


def _require_value(key: str, cli_example: str) -> str:
    """Get a required state value or exit with error."""
    value = get_value(key)
    if not value:
        print(
            f"Error: {key} is required. Use: {cli_example}",
            file=sys.stderr,
        )
        sys.exit(1)
    return str(value)


# Module paths for the sync functions
_COMMANDS_MODULE = "agentic_devtools.cli.azure_devops.commands"
_FILE_REVIEW_MODULE = "agentic_devtools.cli.azure_devops.file_review_commands"
_PIPELINE_MODULE = "agentic_devtools.cli.azure_devops.pipeline_commands"
_REVIEW_MODULE = "agentic_devtools.cli.azure_devops.review_commands"
_PR_DETAILS_MODULE = "agentic_devtools.cli.azure_devops.pull_request_details_commands"
_PR_SUMMARY_MODULE = "agentic_devtools.cli.azure_devops.pr_summary_commands"
_RUN_DETAILS_MODULE = "agentic_devtools.cli.azure_devops.run_details_commands"
_MARK_REVIEWED_MODULE = "agentic_devtools.cli.azure_devops.mark_reviewed"


# =============================================================================
# Pull Request Commands (Async)
# =============================================================================


def add_pull_request_comment_async(
    pull_request_id: Optional[str] = None,
    content: Optional[str] = None,
) -> None:
    """
    Add a comment to a pull request asynchronously in the background.

    Args:
        pull_request_id: PR ID (overrides state)
        content: Comment content (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        content (required): Comment content

    Usage:
        agdt-add-pull-request-comment --pull-request-id 12345 --content "LGTM!"

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-set content "LGTM!"
        agdt-add-pull-request-comment
    """
    # Store CLI args in state if provided
    _set_value_if_provided("pull_request_id", pull_request_id)
    _set_value_if_provided("content", content)

    # Validate required values
    _require_value("pull_request_id", "agdt-add-pull-request-comment --pull-request-id 12345")
    _require_value("content", 'agdt-add-pull-request-comment --content "Your comment"')

    task = run_function_in_background(
        _COMMANDS_MODULE,
        "add_pull_request_comment",
        command_display_name="agdt-add-pull-request-comment",
    )
    print_task_tracking_info(task, "Adding comment to pull request")


def add_pull_request_comment_async_cli() -> None:  # pragma: no cover
    """CLI entry point for add_pull_request_comment_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Add a comment to a pull request (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-add-pull-request-comment --pull-request-id 12345 --content "LGTM!"
  agdt-add-pull-request-comment -p 12345 -c "Looks good to me"

  # Or using state:
  agdt-set pull_request_id 12345
  agdt-set content "LGTM!"
  agdt-add-pull-request-comment
        """,
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=str,
        default=None,
        help="PR ID (falls back to pull_request_id state)",
    )
    parser.add_argument(
        "--content",
        "-c",
        type=str,
        default=None,
        help="Comment content (falls back to content state)",
    )
    args = parser.parse_args()
    add_pull_request_comment_async(
        pull_request_id=args.pull_request_id,
        content=args.content,
    )


def approve_pull_request_async(
    pull_request_id: Optional[str] = None,
    content: Optional[str] = None,
) -> None:
    """
    Approve a pull request asynchronously in the background.

    Args:
        pull_request_id: PR ID (overrides state)
        content: Optional approval comment (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        content (optional): Approval comment

    Usage:
        agdt-approve-pull-request --pull-request-id 12345 --content "LGTM!"

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-approve-pull-request
    """
    # Store CLI args in state if provided
    _set_value_if_provided("pull_request_id", pull_request_id)
    _set_value_if_provided("content", content)

    # Validate required values
    _require_value("pull_request_id", "agdt-approve-pull-request --pull-request-id 12345")

    task = run_function_in_background(
        _COMMANDS_MODULE,
        "approve_pull_request",
        command_display_name="agdt-approve-pull-request",
    )
    print_task_tracking_info(task, "Approving pull request")


def approve_pull_request_async_cli() -> None:  # pragma: no cover
    """CLI entry point for approve_pull_request_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Approve a pull request (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-approve-pull-request --pull-request-id 12345
  agdt-approve-pull-request -p 12345 -c "Approved with comments"

  # Or using state:
  agdt-set pull_request_id 12345
  agdt-approve-pull-request
        """,
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=str,
        default=None,
        help="PR ID (falls back to pull_request_id state)",
    )
    parser.add_argument(
        "--content",
        "-c",
        type=str,
        default=None,
        help="Optional approval comment (falls back to content state)",
    )
    args = parser.parse_args()
    approve_pull_request_async(
        pull_request_id=args.pull_request_id,
        content=args.content,
    )


def create_pull_request_async(
    source_branch: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> None:
    """
    Create a pull request asynchronously in the background.

    Args:
        source_branch: Source branch name (overrides state)
        title: PR title (overrides state)
        description: PR description (overrides state)

    State keys (used as fallbacks):
        source_branch (required): Source branch name
        title (required): PR title
        description (optional): PR description

    Usage:
        agdt-create-pull-request --source-branch "feature/my-feature" --title "Add feature"

        # Or using state:
        agdt-set source_branch "feature/my-feature"
        agdt-set title "Add new feature"
        agdt-create-pull-request
    """
    # Store CLI args in state if provided
    _set_value_if_provided("source_branch", source_branch)
    _set_value_if_provided("title", title)
    _set_value_if_provided("description", description)

    # Validate required values
    _require_value("source_branch", 'agdt-create-pull-request --source-branch "branch-name"')
    _require_value("title", 'agdt-create-pull-request --title "PR title"')

    task = run_function_in_background(
        _COMMANDS_MODULE,
        "create_pull_request",
        command_display_name="agdt-create-pull-request",
    )
    print_task_tracking_info(task, "Creating pull request")


def create_pull_request_async_cli() -> None:
    """CLI entry point for create_pull_request_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Create a pull request (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-create-pull-request --source-branch "feature/my-feature" --title "Add feature"
  agdt-create-pull-request -b "feature/DFLY-1234" -t "feature(DFLY-1234): add feature" -d "Description"

  # Or using state:
  agdt-set source_branch "feature/my-feature"
  agdt-set title "Add new feature"
  agdt-create-pull-request
        """,
    )
    parser.add_argument(
        "--source-branch",
        "-b",
        type=str,
        default=None,
        help="Source branch name (falls back to source_branch state)",
    )
    parser.add_argument(
        "--title",
        "-t",
        type=str,
        default=None,
        help="PR title (falls back to title state)",
    )
    parser.add_argument(
        "--description",
        "-d",
        type=str,
        default=None,
        help="PR description (falls back to description state)",
    )
    args = parser.parse_args()
    create_pull_request_async(
        source_branch=args.source_branch,
        title=args.title,
        description=args.description,
    )


def get_pull_request_threads_async(
    pull_request_id: Optional[str] = None,
) -> None:
    """
    Get pull request threads asynchronously in the background.

    Args:
        pull_request_id: PR ID (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID

    Usage:
        agdt-get-pull-request-threads --pull-request-id 12345

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-get-pull-request-threads
    """
    # Store CLI args in state if provided
    _set_value_if_provided("pull_request_id", pull_request_id)

    # Validate required values
    _require_value("pull_request_id", "agdt-get-pull-request-threads --pull-request-id 12345")

    task = run_function_in_background(
        _COMMANDS_MODULE,
        "get_pull_request_threads",
        command_display_name="agdt-get-pull-request-threads",
    )
    print_task_tracking_info(task, "Getting pull request threads")


def get_pull_request_threads_async_cli() -> None:  # pragma: no cover
    """CLI entry point for get_pull_request_threads_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Get pull request threads (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-get-pull-request-threads --pull-request-id 12345
  agdt-get-pull-request-threads -p 12345

  # Or using state:
  agdt-set pull_request_id 12345
  agdt-get-pull-request-threads
        """,
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=str,
        default=None,
        help="PR ID (falls back to pull_request_id state)",
    )
    args = parser.parse_args()
    get_pull_request_threads_async(
        pull_request_id=args.pull_request_id,
    )


def reply_to_pull_request_thread_async(
    pull_request_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    content: Optional[str] = None,
) -> None:
    """
    Reply to a pull request thread asynchronously in the background.

    Args:
        pull_request_id: PR ID (overrides state)
        thread_id: Thread ID (overrides state)
        content: Reply content (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        thread_id (required): Thread ID
        content (required): Reply content

    Usage:
        agdt-reply-to-pull-request-thread --pull-request-id 12345 --thread-id 67890 --content "Thanks!"

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-set thread_id 67890
        agdt-set content "Thanks for the review!"
        agdt-reply-to-pull-request-thread
    """
    # Store CLI args in state if provided
    _set_value_if_provided("pull_request_id", pull_request_id)
    _set_value_if_provided("thread_id", thread_id)
    _set_value_if_provided("content", content)

    # Validate required values
    _require_value("pull_request_id", "agdt-reply-to-pull-request-thread --pull-request-id 12345")
    _require_value("thread_id", "agdt-reply-to-pull-request-thread --thread-id 67890")
    _require_value("content", 'agdt-reply-to-pull-request-thread --content "Your reply"')

    task = run_function_in_background(
        _COMMANDS_MODULE,
        "reply_to_pull_request_thread",
        command_display_name="agdt-reply-to-pull-request-thread",
    )
    print_task_tracking_info(task, "Replying to pull request thread")


def reply_to_pull_request_thread_async_cli() -> None:  # pragma: no cover
    """CLI entry point for reply_to_pull_request_thread_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Reply to a pull request thread (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-reply-to-pull-request-thread --pull-request-id 12345 --thread-id 67890 --content "Thanks!"
  agdt-reply-to-pull-request-thread -p 12345 -t 67890 -c "Fixed"

  # Or using state:
  agdt-set pull_request_id 12345
  agdt-set thread_id 67890
  agdt-set content "Thanks for the review!"
  agdt-reply-to-pull-request-thread
        """,
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=str,
        default=None,
        help="PR ID (falls back to pull_request_id state)",
    )
    parser.add_argument(
        "--thread-id",
        "-t",
        type=str,
        default=None,
        help="Thread ID (falls back to thread_id state)",
    )
    parser.add_argument(
        "--content",
        "-c",
        type=str,
        default=None,
        help="Reply content (falls back to content state)",
    )
    args = parser.parse_args()
    reply_to_pull_request_thread_async(
        pull_request_id=args.pull_request_id,
        thread_id=args.thread_id,
        content=args.content,
    )


def resolve_thread_async(
    pull_request_id: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> None:
    """
    Resolve a pull request thread asynchronously in the background.

    Args:
        pull_request_id: PR ID (overrides state)
        thread_id: Thread ID (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        thread_id (required): Thread ID

    Usage:
        agdt-resolve-thread --pull-request-id 12345 --thread-id 67890

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-set thread_id 67890
        agdt-resolve-thread
    """
    # Store CLI args in state if provided
    _set_value_if_provided("pull_request_id", pull_request_id)
    _set_value_if_provided("thread_id", thread_id)

    # Validate required values
    _require_value("pull_request_id", "agdt-resolve-thread --pull-request-id 12345")
    _require_value("thread_id", "agdt-resolve-thread --thread-id 67890")

    task = run_function_in_background(
        _COMMANDS_MODULE,
        "resolve_thread",
        command_display_name="agdt-resolve-thread",
    )
    print_task_tracking_info(task, "Resolving pull request thread")


def resolve_thread_async_cli() -> None:  # pragma: no cover
    """CLI entry point for resolve_thread_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Resolve a pull request thread (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-resolve-thread --pull-request-id 12345 --thread-id 67890
  agdt-resolve-thread -p 12345 -t 67890

  # Or using state:
  agdt-set pull_request_id 12345
  agdt-set thread_id 67890
  agdt-resolve-thread
        """,
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=str,
        default=None,
        help="PR ID (falls back to pull_request_id state)",
    )
    parser.add_argument(
        "--thread-id",
        "-t",
        type=str,
        default=None,
        help="Thread ID (falls back to thread_id state)",
    )
    args = parser.parse_args()
    resolve_thread_async(
        pull_request_id=args.pull_request_id,
        thread_id=args.thread_id,
    )


def mark_pull_request_draft_async() -> None:
    """
    Mark a pull request as draft asynchronously in the background.

    State keys:
        pull_request_id (required): PR ID

    Usage:
        agdt-set pull_request_id 12345
        agdt-mark-pull-request-draft
    """
    task = run_function_in_background(
        _COMMANDS_MODULE,
        "mark_pull_request_draft",
        command_display_name="agdt-mark-pull-request-draft",
    )
    print_task_tracking_info(task, "Marking pull request as draft")


def publish_pull_request_async() -> None:
    """
    Publish a pull request (remove draft status) asynchronously in the background.

    State keys:
        pull_request_id (required): PR ID

    Usage:
        agdt-set pull_request_id 12345
        agdt-publish-pull-request
    """
    task = run_function_in_background(
        _COMMANDS_MODULE,
        "publish_pull_request",
        command_display_name="agdt-publish-pull-request",
    )
    print_task_tracking_info(task, "Publishing pull request")


def get_pull_request_details_async() -> None:
    """
    Get pull request details asynchronously in the background.

    State keys:
        pull_request_id (required): PR ID

    Usage:
        agdt-set pull_request_id 12345
        agdt-get-pull-request-details
    """
    task = run_function_in_background(
        _PR_DETAILS_MODULE,
        "get_pull_request_details",
        command_display_name="agdt-get-pull-request-details",
    )
    print_task_tracking_info(task, "Getting pull request details")


# =============================================================================
# Pipeline Commands (Async)
# =============================================================================


def run_e2e_tests_synapse_async() -> None:
    """
    Run Synapse E2E tests pipeline asynchronously in the background.

    State keys:
        branch (required): Branch to test
        e2e.stage: DEV or INT (default: DEV)

    Usage:
        agdt-set branch feature/my-branch
        agdt-set e2e.stage DEV
        agdt-run-e2e-tests-synapse
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "run_e2e_tests_synapse",
        command_display_name="agdt-run-e2e-tests-synapse",
    )
    print_task_tracking_info(task, "Running E2E tests pipeline (Synapse)")


def run_e2e_tests_fabric_async() -> None:
    """
    Run Fabric E2E tests pipeline asynchronously in the background.

    Note: Fabric tests only run in DEV (Fabric DAP is not deployed to INT).

    State keys:
        branch (required): Branch to test

    Usage:
        agdt-set branch feature/my-branch
        agdt-run-e2e-tests-fabric
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "run_e2e_tests_fabric",
        command_display_name="agdt-run-e2e-tests-fabric",
    )
    print_task_tracking_info(task, "Running E2E tests pipeline (Fabric, DEV only)")


def run_wb_patch_async() -> None:
    """
    Run workbench patch pipeline asynchronously in the background.

    State keys:
        workbench (required): Workbench identifier

    Usage:
        agdt-set workbench STND
        agdt-run-wb-patch
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "run_wb_patch",
        command_display_name="agdt-run-wb-patch",
    )
    print_task_tracking_info(task, "Running workbench patch pipeline")


def get_run_details_async() -> None:
    """
    Get pipeline run details asynchronously in the background.

    State keys:
        run_id (required): Pipeline run ID
        pipeline_id (optional): Pipeline definition ID
        fetch_logs (optional): If "true", fetch logs from failed tasks
        vpn_toggle (optional): If "true", temporarily disconnect VPN when fetching logs

    CLI args:
        --fetch-logs: Fetch and save logs from failed tasks
        --vpn-toggle: Temporarily disconnect VPN when fetching logs
        --run-id: Override run_id from state

    Usage:
        agdt-set run_id 12345
        agdt-get-run-details
        agdt-get-run-details --fetch-logs
        agdt-get-run-details --fetch-logs --vpn-toggle
    """
    # Parse CLI args and store in state for background process
    parser = argparse.ArgumentParser(description="Get run details", add_help=False)
    parser.add_argument("--fetch-logs", action="store_true")
    parser.add_argument("--vpn-toggle", action="store_true")
    parser.add_argument("--run-id", type=int)
    args, _ = parser.parse_known_args()

    if args.fetch_logs:  # pragma: no cover
        set_value("fetch_logs", "true")
    if args.vpn_toggle:  # pragma: no cover
        set_value("vpn_toggle", "true")
    if args.run_id:  # pragma: no cover
        set_value("run_id", str(args.run_id))

    task = run_function_in_background(
        _RUN_DETAILS_MODULE,
        "get_run_details",
        command_display_name="agdt-get-run-details",
    )
    print_task_tracking_info(task, "Getting pipeline run details")


def wait_for_run_async() -> None:  # pragma: no cover
    """
    Wait for a pipeline run to complete asynchronously in the background.

    Polls the run status until it finishes. Succeeds when run completes
    (regardless of pipeline result). Only fails if unable to fetch
    run details repeatedly.

    State keys:
        run_id (required): Pipeline run ID
        poll_interval (optional): Seconds between polls (default: 30)
        max_failures (optional): Max consecutive fetch failures (default: 3)
        fetch_logs (optional): If "true", fetch logs from failed tasks
        vpn_toggle (optional): If "true", temporarily disconnect VPN when fetching logs

    CLI args:
        --fetch-logs: Fetch and save logs from failed tasks
        --vpn-toggle: Temporarily disconnect VPN when fetching logs
        --run-id: Override run_id from state
        --poll-interval: Override poll interval from state

    Usage:
        agdt-set run_id 12345
        agdt-wait-for-run
        agdt-wait-for-run --fetch-logs
        agdt-wait-for-run --fetch-logs --vpn-toggle
        agdt-task-wait
    """
    # Parse CLI args and store in state for background process
    parser = argparse.ArgumentParser(description="Wait for run", add_help=False)
    parser.add_argument("--fetch-logs", action="store_true")
    parser.add_argument("--vpn-toggle", action="store_true")
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--poll-interval", type=int)
    args, _ = parser.parse_known_args()

    if args.fetch_logs:
        set_value("fetch_logs", "true")
    if args.vpn_toggle:
        set_value("vpn_toggle", "true")
    if args.run_id:
        set_value("run_id", str(args.run_id))
    if args.poll_interval:
        set_value("poll_interval", str(args.poll_interval))

    task = run_function_in_background(
        _RUN_DETAILS_MODULE,
        "wait_for_run",
        command_display_name="agdt-wait-for-run",
    )
    print_task_tracking_info(task, "Waiting for pipeline run to complete")


def list_pipelines_async() -> None:  # pragma: no cover
    """
    List Azure DevOps pipelines asynchronously in the background.

    State keys:
        pipeline.name_filter (optional): Name or prefix to filter (supports wildcards like "mgmt*")

    Usage:
        agdt-set pipeline.name_filter "mgmt*"
        agdt-list-pipelines
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "list_pipelines",
        command_display_name="agdt-list-pipelines",
    )
    print_task_tracking_info(task, "Listing pipelines")


def get_pipeline_id_async() -> None:  # pragma: no cover
    """
    Get a pipeline ID by name asynchronously in the background.

    State keys:
        pipeline.name (required): Exact name of the pipeline

    Output:
        Sets pipeline.id in state for use by subsequent commands.

    Usage:
        agdt-set pipeline.name "mgmt-e2e-tests"
        agdt-get-pipeline-id
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "get_pipeline_id",
        command_display_name="agdt-get-pipeline-id",
    )
    print_task_tracking_info(task, "Getting pipeline ID")


def create_pipeline_async() -> None:  # pragma: no cover
    """
    Create a new Azure DevOps pipeline asynchronously in the background.

    State keys:
        pipeline.name (required): Name for the new pipeline
        pipeline.yaml_path (required): Path to YAML file in repo (e.g., "/mgmt-frontend/azure-pipelines/file.yml")
        pipeline.description (optional): Description for the pipeline
        pipeline.folder_path (optional): Folder to create pipeline in
        pipeline.skip_first_run (optional): Skip first run (default: true)
        branch (optional): Branch to associate with pipeline (default: main)

    Output:
        Sets pipeline.id in state with the created pipeline's ID.

    Usage:
        agdt-set pipeline.name "mgmt-e2e-tests-fabric"
        agdt-set pipeline.yaml_path "/mgmt-frontend/azure-pipelines/azure-pipelines-e2e-tests-fabric.yml"
        agdt-set pipeline.description "Fabric E2E tests pipeline"
        agdt-create-pipeline
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "create_pipeline",
        command_display_name="agdt-create-pipeline",
    )
    print_task_tracking_info(task, "Creating pipeline")


def update_pipeline_async() -> None:  # pragma: no cover
    """
    Update an existing Azure DevOps pipeline asynchronously in the background.

    State keys:
        pipeline.id (required): ID of pipeline to update (use dfly-get-pipeline-id first)
        pipeline.new_name (optional): New name for the pipeline
        pipeline.yaml_path (optional): New YAML file path
        pipeline.new_folder_path (optional): New folder to move pipeline to
        pipeline.description (optional): New description

    At least one of new_name, yaml_path, new_folder_path, or description must be provided.

    Usage (rename existing pipeline):
        agdt-set pipeline.name "mgmt-e2e-tests"
        agdt-get-pipeline-id  # waits for ID
        agdt-set pipeline.new_name "mgmt-e2e-tests-synapse"
        agdt-set pipeline.yaml_path "/mgmt-frontend/azure-pipelines/azure-pipelines-e2e-tests-synapse.yml"
        agdt-update-pipeline
    """
    task = run_function_in_background(
        _PIPELINE_MODULE,
        "update_pipeline",
        command_display_name="agdt-update-pipeline",
    )
    print_task_tracking_info(task, "Updating pipeline")


# =============================================================================
# File Review Commands (Async)
# =============================================================================


def _auto_advance_after_submission(
    task_id: str,
    file_path: str,
    outcome: str,
) -> None:
    """
    Handle auto-advancement after submitting a file review.

    Marks the file as submission-pending in the queue, then prints
    the next file prompt (or checks for failures).

    Args:
        task_id: Background task ID
        file_path: Path of file being submitted
        outcome: Review outcome ('Approve', 'Changes', 'Suggest')
    """
    from .file_review_commands import (
        mark_file_as_submission_pending,
        print_next_file_prompt,
    )

    pr_id = get_value("pull_request_id")
    if not pr_id:
        return

    pr_id_int = int(pr_id)

    # Mark file as submission-pending
    mark_file_as_submission_pending(pr_id_int, file_path, task_id, outcome)

    # Print the next file prompt
    print_next_file_prompt(pr_id_int)


def approve_file_async(
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    pull_request_id: Optional[int] = None,
) -> None:
    """
    Approve a file in a pull request asynchronously in the background.

    After spawning the background task, immediately marks the file as
    submission-pending and shows the next file to review.

    Args:
        file_path: Path of file to approve (overrides state)
        content: Approval comment content (overrides state)
        pull_request_id: PR ID (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        file_review.file_path (required): Path of file to approve
        content (required): Approval comment

    Usage:
        agdt-approve-file --file-path "src/app/component.ts" --content "LGTM"

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-set file_review.file_path "src/app/component.ts"
        agdt-set content "LGTM"
        agdt-approve-file
    """
    # Store CLI args in state if provided
    _set_value_if_provided("file_review.file_path", file_path)
    _set_value_if_provided("content", content)
    if pull_request_id is not None:
        set_value("pull_request_id", pull_request_id)

    # Validate required values
    _require_value("pull_request_id", "agdt-approve-file --pull-request-id 12345")
    resolved_file_path = _require_value("file_review.file_path", 'agdt-approve-file --file-path "path/to/file"')
    _require_value("content", 'agdt-approve-file --content "Approval comment"')

    task = run_function_in_background(
        _FILE_REVIEW_MODULE,
        "approve_file",
        command_display_name="agdt-approve-file",
    )
    print_task_tracking_info(task, f"Approving file: {resolved_file_path}")

    # Auto-advance: mark as submission-pending and show next file
    _auto_advance_after_submission(task.id, resolved_file_path, "Approve")


def approve_file_async_cli() -> None:
    """CLI entry point for approve_file_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Approve a file in a pull request review (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-approve-file --file-path "src/app/component.ts" --content "LGTM"
  agdt-approve-file --pull-request-id 12345 --file-path "src/app/component.ts" --content "Approved"

  # Or using state:
  agdt-set pull_request_id 12345
  agdt-set file_review.file_path "src/app/component.ts"
  agdt-set content "LGTM"
  agdt-approve-file
        """,
    )
    parser.add_argument(
        "--file-path",
        "-f",
        type=str,
        default=None,
        help="Path of file to approve (falls back to file_review.file_path state)",
    )
    parser.add_argument(
        "--content",
        "-c",
        type=str,
        default=None,
        help="Approval comment content (falls back to content state)",
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=int,
        default=None,
        help="Pull request ID (falls back to pull_request_id state)",
    )
    args = parser.parse_args()
    approve_file_async(
        file_path=args.file_path,
        content=args.content,
        pull_request_id=args.pull_request_id,
    )


def submit_file_review_async() -> None:
    """
    Submit a file review asynchronously in the background.

    State keys:
        pull_request_id (required): PR ID
        file_path (required): Path of file
        content (required): Review content

    Usage:
        agdt-set pull_request_id 12345
        agdt-set file_path "src/app/component.ts"
        agdt-set content "Review comments..."
        agdt-submit-file-review
    """
    task = run_function_in_background(
        _FILE_REVIEW_MODULE,
        "submit_file_review",
        command_display_name="agdt-submit-file-review",
    )
    print_task_tracking_info(task, "Submitting file review")


def request_changes_async(
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    line: Optional[int] = None,
    pull_request_id: Optional[int] = None,
) -> None:
    """
    Request changes on a file asynchronously in the background.

    After spawning the background task, immediately marks the file as
    submission-pending and shows the next file to review.

    Args:
        file_path: Path of file (overrides state)
        content: Change request content (overrides state)
        line: Line number for comment (overrides state)
        pull_request_id: PR ID (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        file_review.file_path (required): Path of file
        content (required): Change request content
        line (required): Line number for comment

    Usage:
        agdt-request-changes --file-path "src/app/component.ts" --content "Issue here" --line 42

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-set file_review.file_path "src/app/component.ts"
        agdt-set content "Please fix this issue..."
        agdt-set line 42
        agdt-request-changes
    """
    # Store CLI args in state if provided
    _set_value_if_provided("file_review.file_path", file_path)
    _set_value_if_provided("content", content)
    if line is not None:
        set_value("line", line)
    if pull_request_id is not None:
        set_value("pull_request_id", pull_request_id)

    # Validate required values
    _require_value("pull_request_id", "agdt-request-changes --pull-request-id 12345")
    resolved_file_path = _require_value("file_review.file_path", 'agdt-request-changes --file-path "path/to/file"')
    _require_value("content", 'agdt-request-changes --content "Issue description"')
    _require_value("line", "agdt-request-changes --line 42")

    task = run_function_in_background(
        _FILE_REVIEW_MODULE,
        "request_changes",
        command_display_name="agdt-request-changes",
    )
    print_task_tracking_info(task, f"Requesting changes on file: {resolved_file_path}")

    # Auto-advance: mark as submission-pending and show next file
    _auto_advance_after_submission(task.id, resolved_file_path, "Changes")


def request_changes_async_cli() -> None:
    """CLI entry point for request_changes_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Request changes on a file in a pull request review (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-request-changes --file-path "src/app/component.ts" --content "Fix this" --line 42
  agdt-request-changes -f "src/main.py" -c "Issue description" -l 100

  # Or using state:
  agdt-set file_review.file_path "src/app/component.ts"
  agdt-set content "Please fix this issue..."
  agdt-set line 42
  agdt-request-changes
        """,
    )
    parser.add_argument(
        "--file-path",
        "-f",
        type=str,
        default=None,
        help="Path of file (falls back to file_review.file_path state)",
    )
    parser.add_argument(
        "--content",
        "-c",
        type=str,
        default=None,
        help="Change request content (falls back to content state)",
    )
    parser.add_argument(
        "--line",
        "-l",
        type=int,
        default=None,
        help="Line number for comment (falls back to line state)",
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=int,
        default=None,
        help="Pull request ID (falls back to pull_request_id state)",
    )
    args = parser.parse_args()
    request_changes_async(
        file_path=args.file_path,
        content=args.content,
        line=args.line,
        pull_request_id=args.pull_request_id,
    )


def request_changes_with_suggestion_async(
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    line: Optional[int] = None,
    pull_request_id: Optional[int] = None,
) -> None:
    """
    Request changes with a code suggestion asynchronously in the background.

    After spawning the background task, immediately marks the file as
    submission-pending and shows the next file to review.

    Args:
        file_path: Path of file (overrides state)
        content: Change request with code suggestion (overrides state)
        line: Line number for comment (overrides state)
        pull_request_id: PR ID (overrides state)

    State keys (used as fallbacks):
        pull_request_id (required): PR ID
        file_review.file_path (required): Path of file
        content (required): Change request with suggestion
        line (required): Line number for comment

    Usage:
        agdt-request-changes-with-suggestion --file-path "src/app/component.ts" --content "```suggestion
        const x = 1;
        ```" --line 42

        # Or using state:
        agdt-set pull_request_id 12345
        agdt-set file_review.file_path "src/app/component.ts"
        agdt-set content "Suggested change..."
        agdt-set line 42
        agdt-request-changes-with-suggestion
    """
    # Store CLI args in state if provided
    _set_value_if_provided("file_review.file_path", file_path)
    _set_value_if_provided("content", content)
    if line is not None:
        set_value("line", line)
    if pull_request_id is not None:
        set_value("pull_request_id", pull_request_id)

    # Validate required values
    _require_value("pull_request_id", "agdt-request-changes-with-suggestion --pull-request-id 12345")
    resolved_file_path = _require_value(
        "file_review.file_path", 'agdt-request-changes-with-suggestion --file-path "path/to/file"'
    )
    _require_value("content", 'agdt-request-changes-with-suggestion --content "Suggestion"')
    _require_value("line", "agdt-request-changes-with-suggestion --line 42")

    task = run_function_in_background(
        _FILE_REVIEW_MODULE,
        "request_changes_with_suggestion",
        command_display_name="agdt-request-changes-with-suggestion",
    )
    print_task_tracking_info(task, f"Requesting changes with suggestion on: {resolved_file_path}")

    # Auto-advance: mark as submission-pending and show next file
    _auto_advance_after_submission(task.id, resolved_file_path, "Suggest")


def request_changes_with_suggestion_async_cli() -> None:
    """CLI entry point for request_changes_with_suggestion_async with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Request changes with code suggestion (async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agdt-request-changes-with-suggestion --file-path "src/app/component.ts" --content "```suggestion
  const x = 1;
  ```" --line 42

  # Or using state:
  agdt-set file_review.file_path "src/app/component.ts"
  agdt-set content "Suggested change..."
  agdt-set line 42
  agdt-request-changes-with-suggestion
        """,
    )
    parser.add_argument(
        "--file-path",
        "-f",
        type=str,
        default=None,
        help="Path of file (falls back to file_review.file_path state)",
    )
    parser.add_argument(
        "--content",
        "-c",
        type=str,
        default=None,
        help="Change request with code suggestion (falls back to content state)",
    )
    parser.add_argument(
        "--line",
        "-l",
        type=int,
        default=None,
        help="Line number for comment (falls back to line state)",
    )
    parser.add_argument(
        "--pull-request-id",
        "-p",
        type=int,
        default=None,
        help="Pull request ID (falls back to pull_request_id state)",
    )
    args = parser.parse_args()
    request_changes_with_suggestion_async(
        file_path=args.file_path,
        content=args.content,
        line=args.line,
        pull_request_id=args.pull_request_id,
    )


def mark_file_reviewed_async() -> None:
    """
    Mark a file as reviewed asynchronously in the background.

    State keys:
        pull_request_id (required): PR ID
        file_path (required): Path of file

    Usage:
        agdt-set pull_request_id 12345
        agdt-set file_path "src/app/component.ts"
        agdt-mark-file-reviewed
    """
    task = run_function_in_background(
        _MARK_REVIEWED_MODULE,
        "mark_file_reviewed_cli",
        command_display_name="agdt-mark-file-reviewed",
    )
    print_task_tracking_info(task, "Marking file as reviewed")


# =============================================================================
# Review Workflow Commands (Async)
# =============================================================================


def checkout_and_sync_branch_async() -> None:  # pragma: no cover
    """
    Checkout PR source branch and sync with main asynchronously.

    This function:
    1. Loads PR details from temp file to get source branch
    2. Checkouts the source branch
    3. Fetches and rebases onto origin/main
    4. Saves files changed on branch to JSON for later use

    State keys:
        pull_request_id (required): PR ID

    Usage:
        agdt-set pull_request_id 12345
        # Then called internally by workflow
    """
    from pathlib import Path

    # Get PR ID from state
    pr_id = get_value("pull_request_id")
    if not pr_id:
        print("Error: pull_request_id is required in state", file=sys.stderr)
        sys.exit(1)

    # Load PR details to get source branch
    scripts_dir = Path(__file__).parent.parent.parent.parent.parent
    temp_dir = scripts_dir / "temp"
    details_path = temp_dir / "temp-get-pull-request-details-response.json"

    if not details_path.exists():
        print(f"Error: PR details file not found: {details_path}", file=sys.stderr)
        print("Run get_pull_request_details first.", file=sys.stderr)
        sys.exit(1)

    import json

    with open(details_path, encoding="utf-8") as f:
        pr_details = json.load(f)

    pr_info = pr_details.get("pullRequest", pr_details)
    source_branch = pr_info.get("sourceRefName", "").replace("refs/heads/", "")

    if not source_branch:
        print("Error: Could not determine source branch from PR details", file=sys.stderr)
        sys.exit(1)

    # Run checkout and sync in background
    task = run_function_in_background(
        _REVIEW_MODULE,
        "checkout_and_sync_branch",
        source_branch,
        int(pr_id),
        True,  # save_files_on_branch=True
        command_display_name="checkout-and-sync-branch",
    )
    print_task_tracking_info(task, f"Checking out branch '{source_branch}' and syncing with main")


def generate_review_prompts_async() -> None:  # pragma: no cover
    """
    Generate review prompts and queue.json asynchronously.

    This function:
    1. Loads PR details from temp file
    2. Loads files_on_branch from JSON (if available)
    3. Generates queue.json and individual file prompts
    4. Initializes the workflow state

    State keys:
        pull_request_id (required): PR ID

    Usage:
        agdt-set pull_request_id 12345
        # Then called internally by workflow
    """
    # Get PR ID from state
    pr_id = get_value("pull_request_id")
    if not pr_id:
        print("Error: pull_request_id is required in state", file=sys.stderr)
        sys.exit(1)

    # Run generate prompts in background
    task = run_function_in_background(
        _REVIEW_MODULE,
        "generate_review_prompts",
        int(pr_id),
        None,  # pr_details - will be loaded from file
        False,  # include_reviewed
        None,  # files_on_branch - will be loaded from file
        command_display_name="generate-review-prompts",
    )
    print_task_tracking_info(task, "Generating review prompts and queue")


def setup_pull_request_review_async(  # pragma: no cover
    pull_request_id: Optional[int] = None,
    jira_issue_key: Optional[str] = None,
) -> None:
    """
    Set up a pull request review asynchronously in the background.

    This is the main entry point for initiating a PR review workflow.
    It orchestrates the complete setup process:
    1. Fetches PR details
    2. Fetches Jira issue details (if key provided)
    3. Checkouts source branch and syncs with main
    4. Generates queue.json and file prompts
    5. Initializes workflow state

    Args:
        pull_request_id: PR ID (uses state if not provided)
        jira_issue_key: Optional Jira issue key (uses state if not provided)

    State keys:
        pull_request_id (required): PR ID
        jira.issue_key (optional): Jira issue key

    Usage:
        agdt-set pull_request_id 12345
        agdt-set jira.issue_key DFLY-1234
        # Then called internally by agdt-initiate-pull-request-review-workflow
    """
    # Get PR ID from parameter or state
    pr_id = pull_request_id
    if pr_id is None:
        pr_id_str = get_value("pull_request_id")
        if not pr_id_str:
            print("Error: pull_request_id is required", file=sys.stderr)
            sys.exit(1)
        pr_id = int(pr_id_str)

    # Get Jira issue key from parameter or state
    jira_key = jira_issue_key
    if jira_key is None:
        jira_key = get_value("jira.issue_key")

    # Ensure values are in state for the background function
    set_value("pull_request_id", pr_id)
    if jira_key:
        set_value("jira.issue_key", jira_key)

    # Run setup in background
    task = run_function_in_background(
        _REVIEW_MODULE,
        "setup_pull_request_review",
        command_display_name="setup-pull-request-review",
    )
    print_task_tracking_info(task, f"Setting up PR #{pr_id} review workflow")


def generate_pr_summary_async() -> None:
    """
    Generate PR summary asynchronously in the background.

    State keys:
        pull_request_id (required): PR ID

    Usage:
        agdt-set pull_request_id 12345
        agdt-generate-pr-summary
    """
    task = run_function_in_background(
        _PR_SUMMARY_MODULE,
        "generate_overarching_pr_comments_cli",
        command_display_name="agdt-generate-pr-summary",
    )
    print_task_tracking_info(task, "Generating PR summary")


# =============================================================================
# Cross-Context Lookup Functions (for context switching)
# =============================================================================


def lookup_jira_issue_from_pr_async(pull_request_id: int) -> None:
    """
    Look up Jira issue key from a PR and save to state.

    Searches for Jira issue key (e.g., DFLY-1234) in:
    1. PR source branch name (e.g., feature/DFLY-1234/my-feature)
    2. PR title
    3. PR description

    This is designed for background execution and silently saves jira.issue_key if found.

    Args:
        pull_request_id: PR ID to look up
    """
    from .helpers import find_jira_issue_from_pr

    try:
        issue_key = find_jira_issue_from_pr(pull_request_id)

        if issue_key:
            # Only set if not already set (avoid overwriting user intent)
            current = get_value("jira.issue_key")
            if not current:
                set_value("jira.issue_key", issue_key)
                print(f"✓ Found Jira issue {issue_key} from PR #{pull_request_id}")
            return

        print(f"ℹ️  No Jira issue key found in PR #{pull_request_id}")

    except Exception as e:
        # Silently fail - this is a background enhancement, not critical
        print(f"⚠️  Could not look up Jira issue from PR: {e}")


def lookup_pr_from_jira_issue_async(issue_key: str) -> None:
    """
    Look up active PR from a Jira issue key and save to state.

    Searches multiple sources in order of reliability:
    1. Jira issue comments/description for PR links (e.g., "PR: #1234")
    2. Azure DevOps PRs where issue key appears in branch/title/description

    This is designed for background execution and silently saves pull_request_id if found.

    Args:
        issue_key: Jira issue key (e.g., "DFLY-1234")
    """
    from .helpers import find_pr_from_jira_issue

    try:
        pr_id = find_pr_from_jira_issue(issue_key)

        if pr_id:
            # Only set if not already set (avoid overwriting user intent)
            current = get_value("pull_request_id")
            if not current:
                set_value("pull_request_id", str(pr_id))
                print(f"✓ Found PR #{pr_id} for Jira issue {issue_key}")
            return

        print(f"ℹ️  No active PR found for Jira issue {issue_key}")

    except Exception as e:
        # Silently fail - this is a background enhancement, not critical
        print(f"⚠️  Could not look up PR from Jira issue: {e}")
