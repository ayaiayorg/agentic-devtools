"""
Worktree setup automation for workflows.

This module provides functions to automatically set up git worktrees
and open VS Code workspaces for workflow execution.
It also includes placeholder issue creation for create workflows.
"""

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

# Exported for dynamic invocation by run_function_in_background
__all__ = ["_setup_worktree_from_state"]


def find_workspace_file(directory: str) -> Optional[str]:
    """
    Find a VS Code workspace file in the given directory.

    Searches for any file matching the ``*.code-workspace`` glob pattern
    in the directory root.  Returns the full path to the first match, or
    ``None`` if no workspace file is found.

    Args:
        directory: Path to the directory to search in.

    Returns:
        Full path to the workspace file, or None if not found.
    """
    try:
        matches = sorted(
            entry.path for entry in os.scandir(directory) if entry.is_file() and entry.name.endswith(".code-workspace")
        )
        return matches[0] if matches else None
    except (FileNotFoundError, NotADirectoryError):
        pass
    except OSError as exc:
        print(f"Warning: unexpected OS error scanning '{directory}': {exc}", file=sys.stderr)
    return None


def generate_workflow_branch_name(
    issue_key: str,
    issue_type: str,
    workflow_name: str,
    parent_key: Optional[str] = None,
) -> str:
    """
    Generate a branch name based on issue type and workflow.

    Patterns:
    - Create workflows: <issueType>/<issue_key>/create-<issueType>
    - Update workflows: <issueType>/<issue_key>/update-<issueType>
    - Subtask create: subtask/<parent_key>/<issue_key>/create-subtask

    Args:
        issue_key: The Jira issue key (e.g., "DFLY-1234")
        issue_type: The issue type (Task, Epic, Sub-task, Bug, etc.)
        workflow_name: The workflow name (create-jira-issue, create-jira-epic, etc.)
        parent_key: For subtasks, the parent issue key (e.g., "DFLY-1233")

    Returns:
        The branch name following the pattern
    """
    # Normalize issue type to lowercase for branch naming
    normalized_type = issue_type.lower().replace(" ", "-")

    # Handle Sub-task specially
    if normalized_type == "sub-task":
        normalized_type = "subtask"

    # Determine workflow action from workflow name
    if "update" in workflow_name.lower():
        action = f"update-{normalized_type}"
    else:
        action = f"create-{normalized_type}"

    # For subtasks with a parent, include parent key
    if normalized_type == "subtask" and parent_key:
        return f"{normalized_type}/{parent_key}/{issue_key}/{action}"

    # Standard pattern: <type>/<key>/<action>
    return f"{normalized_type}/{issue_key}/{action}"


@dataclass
class WorktreeSetupResult:
    """Result of worktree setup operation."""

    success: bool
    worktree_path: str
    branch_name: str
    error_message: Optional[str] = None
    vscode_opened: bool = False


def is_in_worktree() -> bool:
    """
    Check if we're currently in a git worktree (not the main repo).

    Returns:
        True if in a worktree, False if in main repo or not in a git repo.
    """
    try:
        # git rev-parse --is-inside-work-tree returns "true" if in a work tree
        # git worktree list shows all worktrees
        # Simplest check: compare git-dir to git-common-dir
        result_dir = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        result_common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result_dir.returncode != 0 or result_common.returncode != 0:
            return False

        git_dir = Path(result_dir.stdout.strip()).resolve()
        git_common_dir = Path(result_common.stdout.strip()).resolve()

        # In main repo: git_dir == ".git" (resolves to same as git_common_dir)
        # In worktree: git_dir is a file pointing elsewhere, or is different path
        # The git-dir in a worktree points to .git/worktrees/<name>
        return git_dir != git_common_dir

    except (FileNotFoundError, OSError):
        return False


def get_current_branch() -> Optional[str]:
    """
    Get the current git branch name.

    Returns:
        The current branch name, or None if not in a git repo or detached HEAD.
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


def switch_to_main_branch() -> bool:
    """
    Switch to the main branch.

    Returns:
        True if switch was successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "switch", "main"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def get_main_repo_root() -> Optional[str]:
    """
    Get the root directory of the main git repository (not worktree).

    For worktrees, this returns the path to the main repository.
    For the main repo, this returns the repo root.

    Returns:
        The absolute path to the main repo root, or None if not in a git repo.
    """
    try:
        # First, get the common git directory (shared between main repo and worktrees)
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        git_common_dir = result.stdout.strip()

        # The git-common-dir is usually .git in main repo or path/to/main/.git for worktrees
        # We need the parent of the .git directory
        git_path = Path(git_common_dir).resolve()

        # If it ends with .git, go to parent
        if git_path.name == ".git":
            return str(git_path.parent)

        # For worktrees, git-common-dir points to main/.git directly
        return str(git_path.parent)

    except (FileNotFoundError, OSError):
        return None


def get_repos_parent_dir() -> Optional[str]:
    """
    Get the parent directory where repos are stored.

    This is typically one level up from the main repo root (e.g., c:\\repos).

    Returns:
        The absolute path to the repos parent directory, or None if not determinable.
    """
    main_repo = get_main_repo_root()
    if main_repo:
        return str(Path(main_repo).parent)
    return None


def create_worktree(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: Optional[str] = None,
    use_existing_branch: bool = False,
) -> WorktreeSetupResult:
    """
    Create a git worktree for the given issue key.

    The worktree will be created as a sibling directory to the main repo,
    named after the issue key (e.g., ../DFLY-1234).

    Args:
        issue_key: The issue key (e.g., "DFLY-1234")
        branch_prefix: Prefix for the branch name (default: "feature").
            Ignored if branch_name is provided.
        branch_name: Exact branch name to use. If provided, branch_prefix is ignored.
            Used for PR review workflows where the branch already exists on origin.
        use_existing_branch: If True and branch_name is provided, checkout the
            existing branch from origin instead of creating a new one.
            Enables safety checks before proceeding.

    Returns:
        WorktreeSetupResult with success status and paths
    """
    from ..git.operations import (
        check_branch_safe_to_recreate,
        fetch_branch,
    )

    repos_parent = get_repos_parent_dir()
    if not repos_parent:
        return WorktreeSetupResult(
            success=False,
            worktree_path="",
            branch_name="",
            error_message="Could not determine repository parent directory",
        )

    worktree_path = os.path.join(repos_parent, issue_key)

    # Determine the branch name to use
    if branch_name:
        resolved_branch_name = branch_name
    else:
        resolved_branch_name = f"{branch_prefix}/{issue_key}/implementation"

    # Check if worktree already exists
    if os.path.exists(worktree_path):
        # Verify it's a valid git worktree
        git_file = os.path.join(worktree_path, ".git")
        if os.path.exists(git_file):
            return WorktreeSetupResult(
                success=True,
                worktree_path=worktree_path,
                branch_name=resolved_branch_name,
                error_message=None,
            )
        else:
            return WorktreeSetupResult(
                success=False,
                worktree_path=worktree_path,
                branch_name=resolved_branch_name,
                error_message=f"Directory {worktree_path} exists but is not a git worktree",
            )

    # Check if we're currently on the target branch in the main repo.
    # Git doesn't allow creating a worktree for a branch that's already checked out.
    # If we're on the target branch in main repo, we need to switch to main first.
    current_branch = get_current_branch()
    in_worktree = is_in_worktree()

    if current_branch == resolved_branch_name and not in_worktree:
        print(f"Currently on branch '{resolved_branch_name}' in main repo.")
        print("Switching to 'main' branch to allow worktree creation...")
        if not switch_to_main_branch():
            return WorktreeSetupResult(
                success=False,
                worktree_path=worktree_path,
                branch_name=resolved_branch_name,
                error_message="Failed to switch to main branch. Cannot create worktree while on target branch.",
            )
        print("Switched to 'main' branch successfully.")

    # For PR review workflows with existing branches, perform safety checks
    if use_existing_branch and branch_name:
        print(f"Checking if branch '{branch_name}' is safe to use...")

        # First fetch the branch from origin
        fetch_branch(branch_name)

        # Perform safety check
        safety_result = check_branch_safe_to_recreate(branch_name)

        if not safety_result.is_safe:
            return WorktreeSetupResult(
                success=False,
                worktree_path=worktree_path,
                branch_name=resolved_branch_name,
                error_message=f"Cannot safely create worktree:\n{safety_result.message}",
            )

        print(f"Safety check passed: {safety_result.message}")

    # Create the worktree
    try:
        print(f"Creating worktree at {worktree_path}...")

        if use_existing_branch and branch_name:
            # For PR review: checkout existing branch from origin
            result = subprocess.run(
                ["git", "worktree", "add", worktree_path, branch_name],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # Try tracking the remote branch
                result = subprocess.run(
                    ["git", "worktree", "add", worktree_path, "--track", "-b", branch_name, f"origin/{branch_name}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
        else:
            # Standard flow: create new branch
            result = subprocess.run(
                ["git", "worktree", "add", worktree_path, "-b", resolved_branch_name],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # Check if branch already exists - try without -b
                if "already exists" in result.stderr:
                    print(f"Branch {resolved_branch_name} already exists, using existing branch...")
                    result = subprocess.run(
                        ["git", "worktree", "add", worktree_path, resolved_branch_name],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

        if result.returncode != 0:
            return WorktreeSetupResult(
                success=False,
                worktree_path=worktree_path,
                branch_name=resolved_branch_name,
                error_message=f"Failed to create worktree: {result.stderr.strip()}",
            )

        print(f"Worktree created successfully at {worktree_path}")
        return WorktreeSetupResult(
            success=True,
            worktree_path=worktree_path,
            branch_name=resolved_branch_name,
        )

    except (FileNotFoundError, OSError) as e:
        return WorktreeSetupResult(
            success=False,
            worktree_path=worktree_path,
            branch_name=branch_name,
            error_message=f"Error creating worktree: {e}",
        )


def open_vscode_workspace(worktree_path: str) -> bool:
    """
    Open VS Code with the workspace file in the worktree.

    Searches for any ``*.code-workspace`` file in the worktree directory and
    opens it in a new VS Code window.  If no workspace file is found, falls
    back to opening VS Code at the worktree root directory.

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        True if VS Code was opened, False otherwise
    """
    workspace_file = find_workspace_file(worktree_path)

    if workspace_file is None:
        print(
            f"No .code-workspace file found in {worktree_path}, opening folder instead.",
        )
        target = worktree_path
    else:
        target = workspace_file

    print(f"Opening VS Code: {target}")

    try:
        # Open VS Code in a new window (non-blocking)
        # Check actual platform (not mocked) for subprocess flags availability
        if platform.system() == "Windows" and hasattr(subprocess, "DETACHED_PROCESS"):
            # On Windows, 'code' is a .cmd batch file, so we need shell=True
            # to find it via PATH. We also use creationflags to detach the process.
            subprocess.Popen(  # nosec B602 - shell=True required on Windows to find 'code.cmd' via PATH; args is a fixed list
                ["code", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        else:
            # On Unix-like systems, start_new_session works correctly
            subprocess.Popen(
                ["code", target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        print("VS Code window opened")
        return True

    except (FileNotFoundError, OSError) as e:
        print(f"Warning: Could not open VS Code: {e}", file=sys.stderr)
        return False


def setup_worktree_environment(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: Optional[str] = None,
    use_existing_branch: bool = False,
    open_vscode: bool = True,
) -> WorktreeSetupResult:
    """
    Complete worktree setup: create worktree and open VS Code.

    This is the main entry point for setting up a new development environment
    for an issue. It:
    1. Creates a git worktree for the issue
    2. Opens VS Code with the workspace file

    Args:
        issue_key: The issue key (e.g., "DFLY-1234")
        branch_prefix: Prefix for the branch name (default: "feature").
            Ignored if branch_name is provided.
        branch_name: Exact branch name to use. If provided, branch_prefix is ignored.
            Used for PR review workflows where the branch already exists on origin.
        use_existing_branch: If True and branch_name is provided, checkout the
            existing branch from origin instead of creating a new one.
        open_vscode: Whether to open VS Code (default: True)

    Returns:
        WorktreeSetupResult with success status and details
    """
    # Step 1: Create worktree
    result = create_worktree(
        issue_key=issue_key,
        branch_prefix=branch_prefix,
        branch_name=branch_name,
        use_existing_branch=use_existing_branch,
    )

    if not result.success:
        return result

    # Step 2: Open VS Code
    if open_vscode:
        result.vscode_opened = open_vscode_workspace(result.worktree_path)

    return result


def check_worktree_exists(issue_key: str) -> Optional[str]:
    """
    Check if a worktree for the given issue key already exists.

    Args:
        issue_key: The issue key to check for

    Returns:
        The worktree path if it exists, None otherwise
    """
    repos_parent = get_repos_parent_dir()
    if not repos_parent:
        return None

    worktree_path = os.path.join(repos_parent, issue_key)

    if os.path.exists(worktree_path):
        # Verify it's a valid git worktree
        git_file = os.path.join(worktree_path, ".git")
        if os.path.exists(git_file):
            return worktree_path

    return None


def get_worktree_continuation_prompt(
    issue_key: str,
    workflow_name: str,
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
) -> str:
    """
    Generate a prompt for continuing a workflow in a new VS Code window.

    This generates a copy/paste ready command that the user can paste into
    the AI chat in the new VS Code window to continue the workflow.

    Args:
        issue_key: The issue key
        workflow_name: The workflow name (e.g., "work-on-jira-issue", "pull-request-review")
        user_request: The user's explanation/request for what they want
            (AI will use this to populate Jira fields appropriately)
        additional_params: Additional parameters to include in the command
            (e.g., {"pull_request_id": "12345"})

    Returns:
        A formatted prompt string to paste in the new VS Code window
    """
    # Build the base command for each workflow
    workflow_base_commands = {
        "work-on-jira-issue": "agdt-initiate-work-on-jira-issue-workflow",
        "pull-request-review": "agdt-initiate-pull-request-review-workflow",
        "create-jira-issue": "agdt-initiate-create-jira-issue-workflow",
        "create-jira-epic": "agdt-initiate-create-jira-epic-workflow",
        "create-jira-subtask": "agdt-initiate-create-jira-subtask-workflow",
        "update-jira-issue": "agdt-initiate-update-jira-issue-workflow",
    }

    base_command = workflow_base_commands.get(workflow_name, "")

    if not base_command:
        return f"Continue working on issue {issue_key} in the new VS Code window."

    # Build the full command with all parameters
    command_parts = [base_command, f"--issue-key {issue_key}"]

    # Add user-request if provided (for create workflows)
    if user_request:
        # Escape quotes in the value for shell safety
        escaped_request = user_request.replace('"', '\\"')
        command_parts.append(f'--user-request "{escaped_request}"')

    # Add additional parameters if provided
    if additional_params:
        param_order = ["parent_key", "pull_request_id"]
        for param_name in param_order:
            if param_name in additional_params and additional_params[param_name]:
                value = str(additional_params[param_name])
                # Escape quotes in the value for shell safety
                escaped_value = value.replace('"', '\\"')
                cli_param = param_name.replace("_", "-")
                command_parts.append(f'--{cli_param} "{escaped_value}"')

    full_command = " ".join(command_parts)

    # Generate a friendly description of what to do
    return f"""
================================================================================
📋 COPY THE COMMAND BELOW INTO THE NEW VS CODE WINDOW
================================================================================

In the new VS Code window's AI chat (Copilot/Claude), paste this command:

```
{full_command}
```

This will continue the {workflow_name} workflow with all the context preserved.
================================================================================"""


def get_ai_agent_continuation_prompt(
    issue_key: str,
    workflow_name: str = "work-on-jira-issue",
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
) -> str:
    """
    Generate a detailed prompt for AI agents to continue working on an issue.

    This is used when a new VS Code window is opened in a worktree to provide
    the AI agent with clear instructions on how to proceed.

    Args:
        issue_key: The Jira issue key (e.g., "DFLY-1234") or PR identifier (e.g., "PR24031")
        workflow_name: The workflow being executed (e.g., "update-jira-issue")
        user_request: The user's request/explanation for the workflow
        additional_params: Additional parameters for the command (e.g., {"pull_request_id": "24031"})

    Returns:
        A detailed prompt string formatted for AI agents
    """
    # Build the base command for each workflow
    workflow_base_commands = {
        "work-on-jira-issue": "agdt-initiate-work-on-jira-issue-workflow",
        "pull-request-review": "agdt-initiate-pull-request-review-workflow",
        "create-jira-issue": "agdt-initiate-create-jira-issue-workflow",
        "create-jira-epic": "agdt-initiate-create-jira-epic-workflow",
        "create-jira-subtask": "agdt-initiate-create-jira-subtask-workflow",
        "update-jira-issue": "agdt-initiate-update-jira-issue-workflow",
    }

    base_command = workflow_base_commands.get(workflow_name, "agdt-initiate-work-on-jira-issue-workflow")

    # Build the full command with parameters
    # For pull-request-review, use --pull-request-id instead of --issue-key
    if workflow_name == "pull-request-review" and additional_params and additional_params.get("pull_request_id"):
        pull_request_id = additional_params["pull_request_id"]
        command_parts = [base_command, f"--pull-request-id {pull_request_id}"]
    else:
        command_parts = [base_command, f"--issue-key {issue_key}"]

    if user_request:
        # Escape quotes for shell safety
        escaped_request = user_request.replace('"', '\\"')
        command_parts.append(f'--user-request "{escaped_request}"')

    full_command = " ".join(command_parts)

    # Generate workflow-appropriate prompt text
    if workflow_name == "update-jira-issue":
        task_description = "assigned to update a Jira issue's metadata"
        action_description = (
            "update the Jira issue fields (summary, description, acceptance criteria) as specified in the user request"
        )
    elif workflow_name in ("create-jira-issue", "create-jira-epic", "create-jira-subtask"):
        task_description = "assigned to create a new Jira issue"
        action_description = (
            "populate the placeholder Jira issue with proper summary, description, "
            "and acceptance criteria based on the user request"
        )
    elif workflow_name == "pull-request-review":
        task_description = "assigned to review a pull request"
        action_description = "review the pull request thoroughly and provide feedback"
    else:
        task_description = "assigned an issue to work on"
        action_description = "work on the issue until you have completed the workflow"

    return f"""You are a senior software engineer and expert architect who has been {task_description}.

Please run the following command:

{full_command}

to initiate the workflow and then follow the instructions logged to the console to {action_description}.

Work as independently as possible, only pausing to ask questions or seek approval if absolutely \
necessary. As a senior software engineer and expert architect you don't want or need individual \
approval for every command that you execute, so use the example commands which can be auto approved \
and you will be able to develop a quality solution much more efficiently.

It is anyway not sensible to ask questions or ask for approval, because once your work is complete \
another senior software engineer and expert architect in your team will thoroughly review your work. \
So work through the entire process to the best of your abilities knowing that a trusted colleague \
will review it all thoroughly and provide feedback at that time if necessary."""


def setup_worktree_in_background_sync(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: Optional[str] = None,
    use_existing_branch: bool = False,
    workflow_name: str = "work-on-jira-issue",
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
) -> None:
    """
    Perform worktree setup synchronously (called from background task).

    This function is designed to be called from a background task runner.
    It performs the full worktree setup and prints the continuation prompt.

    Args:
        issue_key: The Jira issue key
        branch_prefix: Prefix for the branch name (default: "feature").
            Ignored if branch_name is provided.
        branch_name: Exact branch name to use. If provided, branch_prefix is ignored.
            Used for PR review workflows where the branch already exists on origin.
        use_existing_branch: If True and branch_name is provided, checkout the
            existing branch from origin instead of creating a new one.
        workflow_name: The workflow name for continuation prompt
        user_request: The user's explanation of what they want
        additional_params: Additional parameters for continuation command
    """
    print(f"\n{'=' * 80}")
    print("BACKGROUND WORKTREE SETUP")
    print("=" * 80)

    # Check if worktree already exists
    existing_path = check_worktree_exists(issue_key)
    if existing_path:
        print(f"\nWorktree already exists at: {existing_path}")
        print("Opening VS Code in the existing worktree (using the workspace file if available)...")

        # Open VS Code
        vscode_opened = open_vscode_workspace(existing_path)
        print(f"   VS Code opened: {'Yes' if vscode_opened else 'No'}")

        print("\n✅ Environment ready!")
        print(get_worktree_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("\n" + "=" * 80)
        print("AI AGENT INSTRUCTIONS - IMPORTANT")
        print("=" * 80)
        print("""
Please provide the following prompt in your chat response to the user so they
can copy and paste it into the new VS Code window that just opened:
""")
        print("--- BEGIN PROMPT FOR USER TO COPY ---")
        print(get_ai_agent_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("--- END PROMPT FOR USER TO COPY ---")
        return

    # Create new worktree environment
    print(f"\nCreating worktree for issue {issue_key}...")
    if use_existing_branch and branch_name:
        print(f"   Using existing branch from origin: {branch_name}")

    result = setup_worktree_environment(
        issue_key=issue_key,
        branch_prefix=branch_prefix,
        branch_name=branch_name,
        use_existing_branch=use_existing_branch,
        open_vscode=True,
    )

    if result.success:
        print("\n✅ Environment setup complete!")
        print(f"   Worktree: {result.worktree_path}")
        print(f"   Branch: {result.branch_name}")
        print(f"   VS Code opened: {'Yes' if result.vscode_opened else 'No'}")
        print(get_worktree_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("\n" + "=" * 80)
        print("AI AGENT INSTRUCTIONS - IMPORTANT")
        print("=" * 80)
        print("""
Please provide the following prompt in your chat response to the user so they
can copy and paste it into the new VS Code window that just opened:
""")
        print("--- BEGIN PROMPT FOR USER TO COPY ---")
        print(get_ai_agent_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("--- END PROMPT FOR USER TO COPY ---")
    else:
        print(f"\n❌ Setup failed: {result.error_message}")
        raise RuntimeError(f"Worktree setup failed: {result.error_message}")


def _setup_worktree_from_state() -> None:
    """
    Wrapper function for background task execution.

    This function is called dynamically by run_function_in_background
    via string reference (see __all__ export at module top).

    This reads parameters from state and calls setup_worktree_in_background_sync.
    Used by run_function_in_background since it only supports parameterless functions.
    """
    import json

    from ...state import get_value

    # Read parameters from state
    issue_key = get_value("worktree_setup.issue_key")
    branch_prefix = get_value("worktree_setup.branch_prefix") or "feature"
    branch_name = get_value("worktree_setup.branch_name")
    use_existing_branch = get_value("worktree_setup.use_existing_branch") == "true"
    workflow_name = get_value("worktree_setup.workflow_name") or "work-on-jira-issue"
    user_request = get_value("worktree_setup.user_request")
    additional_params_str = get_value("worktree_setup.additional_params")

    additional_params = None
    if additional_params_str:
        try:
            additional_params = json.loads(additional_params_str)
        except json.JSONDecodeError:
            pass

    if not issue_key:
        raise ValueError("worktree_setup.issue_key not set in state")

    # Call the actual setup function
    setup_worktree_in_background_sync(
        issue_key=issue_key,
        branch_prefix=branch_prefix,
        branch_name=branch_name,
        use_existing_branch=use_existing_branch,
        workflow_name=workflow_name,
        user_request=user_request,
        additional_params=additional_params,
    )


def start_worktree_setup_background(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: Optional[str] = None,
    use_existing_branch: bool = False,
    workflow_name: str = "work-on-jira-issue",
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
) -> str:
    """
    Start worktree setup as a background task.

    This spawns a background process to create the worktree, install helpers,
    and open VS Code. The calling process returns immediately, allowing the
    command line to be available.

    Args:
        issue_key: The Jira issue key
        branch_prefix: Prefix for the branch name (default: "feature").
            Ignored if branch_name is provided.
        branch_name: Exact branch name to use. If provided, branch_prefix is ignored.
            Used for PR review workflows where the branch already exists on origin.
        use_existing_branch: If True and branch_name is provided, checkout the
            existing branch from origin instead of creating a new one.
        workflow_name: The workflow name for continuation prompt
        user_request: The user's explanation of what they want
        additional_params: Additional parameters for continuation command

    Returns:
        The background task ID for tracking progress
    """
    import json

    from ...background_tasks import run_function_in_background
    from ...state import set_value

    # Store parameters in state for the background function to read
    set_value("worktree_setup.issue_key", issue_key)
    set_value("worktree_setup.branch_prefix", branch_prefix)
    set_value("worktree_setup.workflow_name", workflow_name)
    if branch_name:
        set_value("worktree_setup.branch_name", branch_name)
    if use_existing_branch:
        set_value("worktree_setup.use_existing_branch", "true")
    if user_request:
        set_value("worktree_setup.user_request", user_request)
    if additional_params:
        set_value("worktree_setup.additional_params", json.dumps(additional_params))

    # Build display name for the task
    display_name = f"agdt-setup-worktree-background --issue-key {issue_key}"

    # Start background task using function-based runner
    # This avoids the need for global CLI commands to be installed
    task = run_function_in_background(
        module_path="agentic_devtools.cli.workflows.worktree_setup",
        function_name="_setup_worktree_from_state",
        command_display_name=display_name,
        args={
            "issue_key": issue_key,
            "branch_prefix": branch_prefix,
            "branch_name": branch_name,
            "use_existing_branch": use_existing_branch,
            "workflow_name": workflow_name,
        },
    )

    return task.id


# =============================================================================
# Placeholder Issue Creation for Create Workflows
# =============================================================================


@dataclass
class PlaceholderIssueResult:
    """Result of placeholder issue creation."""

    success: bool
    issue_key: Optional[str] = None
    error_message: Optional[str] = None


def create_placeholder_issue(
    project_key: str,
    issue_type: str = "Task",
    parent_key: Optional[str] = None,
) -> PlaceholderIssueResult:
    """
    Create a placeholder Jira issue with minimal fields.

    This creates an issue with a placeholder summary and description
    that will be updated later in the workflow.

    Args:
        project_key: Jira project key (e.g., "DFLY")
        issue_type: Issue type (Task, Epic, Sub-task)
        parent_key: Parent issue key (required for Sub-task type)

    Returns:
        PlaceholderIssueResult with success status and issue key
    """
    try:
        from ..jira.create_commands import create_issue_sync

        # Generate placeholder values
        placeholder_summary = f"[Placeholder] {issue_type} created via workflow"
        placeholder_description = (
            "This issue was created as a placeholder by the workflow automation.\n\n"
            "Please update the summary, description, and other fields as needed."
        )
        placeholder_labels = ["workflow-placeholder"]

        # For Epic, we need an epic name
        epic_name = None
        if issue_type.lower() == "epic":
            epic_name = placeholder_summary

        print(f"Creating placeholder {issue_type} in project {project_key}...")

        result = create_issue_sync(
            project_key=project_key,
            summary=placeholder_summary,
            issue_type=issue_type,
            description=placeholder_description,
            labels=placeholder_labels,
            epic_name=epic_name,
            parent_key=parent_key,
        )

        issue_key = result.get("key")
        if issue_key:
            print(f"✅ Placeholder {issue_type} created: {issue_key}")
            return PlaceholderIssueResult(success=True, issue_key=issue_key)
        else:
            return PlaceholderIssueResult(
                success=False,
                error_message="API did not return an issue key",
            )

    except Exception as e:
        return PlaceholderIssueResult(
            success=False,
            error_message=str(e),
        )


def create_placeholder_and_setup_worktree(
    project_key: str,
    issue_type: str = "Task",
    parent_key: Optional[str] = None,
    workflow_name: str = "create-jira-issue",
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Create a placeholder issue and set up a worktree for it.

    This is the main entry point for create workflows that need both
    issue creation and environment setup.

    Args:
        project_key: Jira project key (e.g., "DFLY")
        issue_type: Issue type (Task, Epic, Sub-task)
        parent_key: Parent issue key (required for Sub-task type)
        workflow_name: Name of the workflow for continuation prompt
        user_request: The user's explanation of what they want to create
            (AI will use this to populate Jira fields appropriately)
        additional_params: Additional parameters to include in the continuation
            command (e.g., {"parent_key": "DFLY-1234"})

    Returns:
        Tuple of (success, issue_key). If success is True, issue_key contains
        the created issue key. If success is False, issue_key is None.
    """
    print(f"\n{'=' * 80}")
    print(f"CREATE WORKFLOW: {workflow_name}")
    print("=" * 80)

    # Step 1: Create placeholder issue
    print("\n📝 Step 1: Creating placeholder Jira issue...")
    issue_result = create_placeholder_issue(
        project_key=project_key,
        issue_type=issue_type,
        parent_key=parent_key,
    )

    if not issue_result.success:
        print(f"\n❌ Failed to create placeholder issue: {issue_result.error_message}")
        return False, None

    issue_key = issue_result.issue_key
    print(f"   Issue key: {issue_key}")

    # Set the issue key in state for later use
    from ...state import set_value

    set_value("jira.issue_key", issue_key)

    # Step 2: Set up worktree environment
    print("\n🔧 Step 2: Setting up worktree environment...")

    # Check if worktree already exists (unlikely for new issue, but check anyway)
    existing_path = check_worktree_exists(issue_key)
    if existing_path:
        print(f"   Worktree already exists at: {existing_path}")
        open_vscode_workspace(existing_path)
        print(get_worktree_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        return True, issue_key

    # Generate branch name based on issue type and workflow
    branch_name = generate_workflow_branch_name(
        issue_key=issue_key,
        issue_type=issue_type,
        workflow_name=workflow_name,
        parent_key=parent_key,
    )

    # Create new worktree with generated branch name
    result = setup_worktree_environment(
        issue_key=issue_key,
        branch_name=branch_name,
        open_vscode=True,
    )

    if result.success:
        print("\n✅ Environment setup complete!")
        print(f"   Worktree: {result.worktree_path}")
        print(f"   Branch: {result.branch_name}")
        print(f"   VS Code opened: {'Yes' if result.vscode_opened else 'No'}")
        print(get_worktree_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        return True, issue_key
    else:
        print(f"\n❌ Worktree setup failed: {result.error_message}")
        print(f"   Issue {issue_key} was created but environment setup failed.")
        print("   Please set up the worktree manually:")
        print(f"   git worktree add ../{issue_key} -b {branch_name}")
        return False, issue_key
