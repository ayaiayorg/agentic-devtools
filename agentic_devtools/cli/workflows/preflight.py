"""
Pre-flight checks for workflow initiation.

This module provides functions to validate the environment before
starting a workflow, such as checking if the current directory and
git branch match the expected Jira issue key.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

_WORKFLOW_AUTO_EXECUTE_TIMEOUTS: dict[str, int] = {
    "pull-request-review": 600,
    "apply-pull-request-review-suggestions": 300,
}


@dataclass
class PreflightResult:
    """Result of pre-flight checks for workflow initiation."""

    folder_valid: bool
    branch_valid: bool
    folder_name: str
    branch_name: str
    issue_key: str
    repo_root: str | None = None
    # For PR review workflows, tracks if we matched by source branch instead of issue key
    matched_by_source_branch: bool = False

    @property
    def passed(self) -> bool:
        """Check if all pre-flight checks passed."""
        return self.folder_valid and self.branch_valid

    @property
    def failure_reasons(self) -> list[str]:
        """Get list of reasons why pre-flight failed."""
        reasons = []
        if not self.folder_valid:
            reasons.append(f"Folder '{self.folder_name}' does not contain issue key '{self.issue_key}'")
        if not self.branch_valid:
            if self.branch_name:
                reasons.append(f"Branch '{self.branch_name}' does not contain issue key '{self.issue_key}'")
            else:
                reasons.append("Not in a git repository or no branch checked out")
        return reasons


def get_current_git_branch() -> str | None:
    """
    Get the current git branch name.

    Returns:
        The current branch name, or None if not in a git repo or no branch checked out.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
        return None
    except (FileNotFoundError, OSError):
        return None


def get_git_repo_root() -> str | None:
    """
    Get the root directory of the current git repository.

    Returns:
        The absolute path to the repo root, or None if not in a git repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (FileNotFoundError, OSError):  # pragma: no cover
        return None


def check_worktree_and_branch(
    issue_key: str,
    source_branch: str | None = None,
) -> PreflightResult:
    """
    Check if the current worktree folder and git branch contain the issue key.

    This validates that the developer is working in the correct context
    for the given Jira issue. Both the worktree root folder name and branch name
    should contain the issue key (case-insensitive).

    For PR review workflows without a Jira issue, the issue_key will be "PR{pr_id}"
    and source_branch should be provided. In this case, the branch validation passes
    if the current branch matches the source_branch exactly.

    Args:
        issue_key: The Jira issue key to check for (e.g., "PROJECT-1850") or PR identifier (e.g., "PR24031")
        source_branch: Optional source branch for PR review workflows. If provided and
                       the branch doesn't contain the issue_key, we check for exact match
                       with this branch name.

    Returns:
        PreflightResult with validation status and details
    """
    # Get git repo root - this is the worktree folder we care about
    repo_root = get_git_repo_root()

    if repo_root:
        folder_name = Path(repo_root).name
    else:
        # Fallback to cwd if not in a git repo
        folder_name = Path.cwd().name

    # Check if worktree folder contains issue key (case-insensitive)
    folder_valid = issue_key.upper() in folder_name.upper()

    # Get current git branch
    branch_name = get_current_git_branch() or ""

    # Check if branch contains issue key (case-insensitive)
    branch_contains_key = bool(branch_name and issue_key.upper() in branch_name.upper())

    # For PR review workflows, also check if current branch matches the source branch
    matched_by_source_branch = False
    if not branch_contains_key and source_branch:
        # Normalize branch names for comparison (strip refs/heads/ if present)
        normalized_current = branch_name.replace("refs/heads/", "")
        normalized_source = source_branch.replace("refs/heads/", "")
        if normalized_current and normalized_current == normalized_source:
            branch_contains_key = True
            matched_by_source_branch = True

    return PreflightResult(
        folder_valid=folder_valid,
        branch_valid=branch_contains_key,
        folder_name=folder_name,
        branch_name=branch_name,
        issue_key=issue_key,
        repo_root=repo_root,
        matched_by_source_branch=matched_by_source_branch,
    )


def generate_setup_instructions(issue_key: str, preflight_result: PreflightResult) -> str:
    """
    Generate setup instructions when pre-flight checks fail.

    Args:
        issue_key: The Jira issue key
        preflight_result: The result of pre-flight checks

    Returns:
        Formatted instructions for setting up the correct environment
    """
    lines = [
        "# Workflow Setup Required",
        "",
        "Pre-flight checks failed. Please set up your environment:",
        "",
    ]

    # Add failure reasons
    lines.append("## Issues Detected")
    for reason in preflight_result.failure_reasons:
        lines.append(f"- {reason}")
    lines.append("")

    # Generate worktree command if folder is wrong
    if not preflight_result.folder_valid:
        lines.extend(
            [
                "## Create Worktree",
                "",
                "Run these commands to create a dedicated worktree for this issue:",
                "",
                "```bash",
                "# From your main repo directory:",
                f"git worktree add ../{issue_key} -b feature/{issue_key}/implementation",
                "```",
                "",
            ]
        )

    # Generate branch command if only branch is wrong
    elif not preflight_result.branch_valid:
        lines.extend(
            [
                "## Create Feature Branch",
                "",
                "Run this command to create a feature branch:",
                "",
                "```bash",
                f"git switch -c feature/{issue_key}/implementation",
                "```",
                "",
            ]
        )

    # VS Code open command
    lines.extend(
        [
            "## Open in VS Code",
            "",
            "After creating the worktree/branch, open VS Code in the new directory:",
            "",
            "```bash",
            f"code ../{issue_key}/agdt-platform-management.code-workspace",
            "```",
            "",
        ]
    )

    # Paste prompt for new window
    lines.extend(
        [
            "## Continue Workflow",
            "",
            "A Copilot session will start automatically in the new VS Code window.",
            "If the session doesn't start, paste this prompt to continue:",
            "",
            "```",
            f"Work on Jira issue {issue_key}",
            "```",
            "",
            "This command is a fallback — normally the session starts automatically.",
        ]
    )

    return "\n".join(lines)


def perform_auto_setup(
    issue_key: str,
    workflow_name: str,
    branch_prefix: str = "feature",
    branch_name: str | None = None,
    use_existing_branch: bool = False,
    user_request: str | None = None,
    additional_params: dict | None = None,
    auto_execute_command: list[str] | None = None,
    auto_execute_timeout: int | None = None,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """
    Automatically set up a worktree environment for the issue as a background task.

    This spawns a background task to create the worktree, install agentic-devtools,
    and open VS Code. The command line is immediately available after spawning the task.

    The background task will output:
    1. Progress updates during setup
    2. A continuation prompt for the AI agent when complete

    Use `agdt-task-log` to see the output including the AI agent prompt.

    Args:
        issue_key: The Jira issue key
        workflow_name: The workflow name for continuation prompt
        branch_prefix: Prefix for the branch name (default: "feature").
            Ignored if branch_name is provided.
        branch_name: Exact branch name to use. If provided, branch_prefix is ignored.
            Used for PR review workflows where the branch already exists on origin.
        use_existing_branch: If True and branch_name is provided, checkout the
            existing branch from origin instead of creating a new one.
        user_request: The user's explanation of what they want (for create workflows)
        additional_params: Additional parameters to include in the continuation
            command (e.g., {"parent_key": "PROJECT-1234", "pull_request_id": "12345"})
        auto_execute_command: Optional command to run inside the worktree after
            creation. Passed through to the background setup task.
        auto_execute_timeout: Timeout in seconds for the auto-execute command.
            When None (default), uses workflow-specific defaults (e.g., 300s
            for pull-request-review) or falls back to 60s. Pass an explicit
            value to override the workflow default.
        interactive: Whether to start the Copilot session interactively after
            the worktree is ready (default: False). Set to True for interactive mode.
        model: The Copilot model ID to use (e.g., "gpt-4o"). When provided,
            passed explicitly to the background setup task instead of relying
            on copilot.model_id state.

    Returns:
        True if the background task was started, False otherwise
    """
    from ...state import set_value
    from .worktree_setup import start_worktree_setup_background

    # Resolve workflow-specific timeout when caller used the signature default.
    if auto_execute_timeout is None:
        auto_execute_timeout = _WORKFLOW_AUTO_EXECUTE_TIMEOUTS.get(workflow_name, 60)

    print(f"\n{'=' * 80}")
    print("AUTOMATIC ENVIRONMENT SETUP (BACKGROUND)")
    print("=" * 80)
    print(f"\nStarting background task to set up worktree for {issue_key}...")

    try:
        task_id = start_worktree_setup_background(
            issue_key=issue_key,
            branch_prefix=branch_prefix,
            branch_name=branch_name,
            use_existing_branch=use_existing_branch,
            workflow_name=workflow_name,
            user_request=user_request,
            additional_params=additional_params,
            auto_execute_command=auto_execute_command,
            auto_execute_timeout=auto_execute_timeout,
            interactive=interactive,
            model=model,
        )

        # Automatically save the task ID to state so agdt-task-wait works
        # without requiring the user to manually set background.task_id.
        set_value("background.task_id", task_id)

        print(f"\n✅ Background task started: {task_id}")
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("""
The worktree setup is running in the background.
A Copilot session will start automatically in the VS Code integrated terminal when the worktree is ready.

If the session doesn't start automatically:
  1. Run: agdt-task-log
     Look for the "AI AGENT INSTRUCTIONS (FALLBACK)" section.
  2. Or run: agdt-task-wait
     This waits for the task to complete, then check the log.
""")
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Failed to start background task: {e}")
        return False
