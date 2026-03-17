"""
Worktree setup automation for workflows.

This module provides functions to automatically set up git worktrees
and open VS Code workspaces for workflow execution.
It also includes placeholder issue creation for create workflows.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Exported for dynamic invocation by run_function_in_background
__all__ = ["_setup_worktree_from_state"]

# Static single-line prompt used when starting the Copilot CLI session for PR
# review.  It contains *only* the instruction to run the first advance command
# so the agent is forced into the workflow system before receiving any context.
# MUST remain a single line (no ``\n``).  Use ``---`` as visual separators.
COPILOT_SESSION_START_PROMPT = (
    "You are a senior software engineer reviewing a Pull Request. "
    "--- CRITICAL: Execute this command now: `agdt-advance-workflow pull-request-overview` "
    "--- This command will provide you with all PR details, review criteria, and instructions. "
    "Do NOT attempt to review any code or gather any information until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

# ---------------------------------------------------------------------------
# Workflow-specific Copilot session start prompts
# Each MUST remain a single line (no ``\n``) and contain no template variables.
# ---------------------------------------------------------------------------

COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS = (
    "You are applying pull request review suggestions. "
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the rendered prompt file containing full instructions "
    "on which review suggestions to apply and how. "
    "Do NOT attempt to modify any code until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)


COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE = (
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the work-on-jira-issue workflow instructions. "
    "Do NOT attempt any work until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_CREATE_JIRA_ISSUE = (
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the create-jira-issue workflow instructions. "
    "Do NOT attempt any work until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_CREATE_JIRA_EPIC = (
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the create-jira-epic workflow instructions. "
    "Do NOT attempt any work until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_CREATE_JIRA_SUBTASK = (
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the create-jira-subtask workflow instructions. "
    "Do NOT attempt any work until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_UPDATE_JIRA_ISSUE = (
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the update-jira-issue workflow instructions. "
    "Do NOT attempt any work until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

# Workflow-agnostic fallback prompt used when ``workflow_name`` is not found in
# ``_WORKFLOW_START_PROMPTS``.  This instructs the agent to run
# ``agdt-get-next-workflow-prompt`` which re-renders the current step regardless
# of the specific workflow, so it's always safe to use as a default.
_WORKFLOW_AGNOSTIC_FALLBACK_PROMPT = (
    "--- CRITICAL: Execute this command now: `agdt-get-next-workflow-prompt` "
    "--- This command will provide you with the current workflow instructions. "
    "Do NOT attempt any work until you have run this command. "
    "The agentic-devtools workflow will guide you through each step."
)

# Mapping from workflow name → start prompt used by the VS Code auto-start task
# injector.  Workflow names not listed here fall back to the workflow-agnostic
# prompt (``_WORKFLOW_AGNOSTIC_FALLBACK_PROMPT``).
_WORKFLOW_START_PROMPTS: dict[str, str] = {
    "pull-request-review": COPILOT_SESSION_START_PROMPT,
    "apply-pull-request-review-suggestions": COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS,
    "work-on-jira-issue": COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
    "create-jira-issue": COPILOT_SESSION_START_PROMPT_CREATE_JIRA_ISSUE,
    "create-jira-epic": COPILOT_SESSION_START_PROMPT_CREATE_JIRA_EPIC,
    "create-jira-subtask": COPILOT_SESSION_START_PROMPT_CREATE_JIRA_SUBTASK,
    "update-jira-issue": COPILOT_SESSION_START_PROMPT_UPDATE_JIRA_ISSUE,
}


def is_vscode_available() -> bool:
    """Check if VS Code CLI is available on PATH.

    Returns:
        True if the ``code`` command is found on PATH, False otherwise.
    """
    return shutil.which("code") is not None


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
    except (FileNotFoundError, OSError):  # pragma: no cover
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
    if not is_vscode_available():
        print("VS Code not found on PATH — skipping window opening", file=sys.stderr)
        return False

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


def _detect_git_root() -> str:
    """
    Detect the Git for Windows installation root directory.

    Attempts to find the Git executable using ``where.exe`` and derives the
    installation root from its path.  Falls back to
    ``C:\\Program Files\\Git`` if detection fails.

    Returns:
        Absolute path to the Git installation root directory.
    """
    from pathlib import PureWindowsPath

    fallback = r"C:\Program Files\Git"
    try:
        result = subprocess.run(
            ["where.exe", "git"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            stdout_stripped = result.stdout.strip()
            if stdout_stripped:
                git_exe = stdout_stripped.splitlines()[0]
                git_path = PureWindowsPath(git_exe)
                # git.exe lives in <root>\cmd\git.exe or <root>\bin\git.exe
                if git_path.parent.name.lower() in ("cmd", "bin"):
                    return str(git_path.parent.parent)
    except (FileNotFoundError, OSError):
        pass
    return fallback


def inject_git_path_settings(worktree_path: str) -> None:
    """
    Inject ``.vscode/settings.json`` into the worktree with Git for Windows PATH entries.

    VS Code terminal sessions opened in a fresh worktree window on Windows may
    not inherit the full PATH that includes Git for Windows' internal binary
    directories (``cmd`` and ``usr\\bin``).  Without those directories, ``git
    push`` and other operations that shell out to credential helpers or internal
    utilities fail silently with exit code 128.

    This function creates or merges into ``.vscode/settings.json`` a
    ``terminal.integrated.env.windows`` entry that appends both
    ``<git_root>\\cmd`` and ``<git_root>\\usr\\bin`` to PATH.

    This function is a no-op on non-Windows platforms.

    Args:
        worktree_path: Path to the worktree directory.
    """
    if platform.system() != "Windows":
        return

    if not is_vscode_available():
        print("VS Code not found on PATH — skipping settings injection", file=sys.stderr)
        return

    git_root = _detect_git_root()
    # Use explicit backslash joining so paths are correct Windows paths
    # regardless of the host OS (e.g. when tests run on Linux).
    git_cmd_dir = git_root + "\\cmd"
    git_usr_bin_dir = git_root + "\\usr\\bin"

    vscode_dir = os.path.join(worktree_path, ".vscode")
    settings_path = os.path.join(vscode_dir, "settings.json")

    settings: dict = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as fh:
                settings = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: could not read {settings_path}: {exc}", file=sys.stderr)
            settings = {}

    env_windows: dict = settings.setdefault("terminal.integrated.env.windows", {})
    existing_path: str = env_windows.get("PATH", "${env:PATH}")
    # Split PATH into segments and compare case-insensitively to avoid both
    # false positives from substring matches and missed entries on the
    # case-insensitive Windows filesystem.
    path_segments = {seg.casefold() for seg in existing_path.split(";") if seg}
    missing_dirs = [d for d in (git_cmd_dir, git_usr_bin_dir) if d.casefold() not in path_segments]
    if missing_dirs:
        env_windows["PATH"] = existing_path + ";" + ";".join(missing_dirs)

    try:
        os.makedirs(vscode_dir, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
            fh.write("\n")
        if missing_dirs:
            print(f"Injected Git PATH settings into {settings_path}")
        else:
            print(f"Git PATH settings already configured in {settings_path}")
    except OSError as exc:
        print(f"Warning: could not write {settings_path}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Label used to identify the injected auto-start task so it can be removed
# during cleanup without affecting other user-defined tasks.
# ---------------------------------------------------------------------------
_AUTO_START_TASK_LABEL = "agdt-copilot-auto-start"


def _build_cleanup_shell_command(
    worktree_path: str,
    task_label: str,
    created_new: bool = False,
) -> str:
    """Build a platform-appropriate shell snippet that removes the injected task.

    The snippet removes only the task identified by *task_label* from
    ``.vscode/tasks.json``.  When other tasks remain the file is rewritten
    without the injected entry, preserving top-level keys (e.g. ``inputs``,
    ``options``).

    When *created_new* is ``True`` and no tasks remain after removal the
    file is **deleted** (rather than rewritten with an empty ``tasks``
    array), and the ``.vscode/`` directory is also removed if it is empty.
    This avoids leaving behind an untracked file in repositories where
    ``.vscode/`` is not gitignored.  When *created_new* is ``False`` (the
    default) the file is always rewritten — even with an empty ``tasks``
    array — so that pre-existing top-level keys are preserved.

    On Unix the snippet uses ``python3``; on Windows it uses ``python``.
    Both paths use an inline Python one-liner for JSON manipulation so the
    cleanup does not depend on ``jq``, ``sed``, or PowerShell-specific
    cmdlets.

    Args:
        worktree_path: Absolute path to the worktree directory.
        task_label: The label identifying the task to remove.
        created_new: ``True`` when ``tasks.json`` was created by the
            injection (did not exist beforehand).  Enables full file
            deletion when the tasks array is empty after cleanup.

    Returns:
        A shell command string suitable for embedding in a VS Code task.
    """
    tasks_json_path = os.path.join(worktree_path, ".vscode", "tasks.json")
    # Use forward slashes universally — Python's ``json``/``os`` on Windows
    # handles them fine, and it avoids escaping issues in shell strings.
    tasks_json_path = tasks_json_path.replace("\\", "/")

    python_cmd = "python" if platform.system() == "Windows" else "python3"

    # Inline Python one-liner:
    #   1. Read tasks.json
    #   2. Remove the task matching the label
    #   3a. If tasks remain → rewrite the file (always)
    #   3b. If no tasks remain AND created_new → delete the file (and
    #       try to rmdir .vscode/ if empty)
    #   3c. If no tasks remain AND NOT created_new → rewrite with empty
    #       tasks array (preserving other top-level keys)
    # Use repr() for embedded string literals to prevent injection from
    # paths or labels containing quotes.  Use encoding='utf-8' for all
    # file I/O to avoid platform-default encoding on Windows.
    # Note: repr() may produce double-quoted strings (e.g. when the value
    # contains a single quote).  Shell-special characters ($, `, ", \) in
    # the resulting py_script are escaped before embedding in the outer
    # -c "..." argument — see the escaping block below.
    p_repr = repr(tasks_json_path)
    label_repr = repr(task_label)

    filter_stmt = f"d['tasks']=[t for t in d.get('tasks',[]) if not isinstance(t,dict) or t.get('label')!={label_repr}]"

    if created_new:
        # When the file was created solely for auto-start: delete it when
        # no tasks remain, and try to remove .vscode/ if it's now empty.
        py_script = (
            "import json, os; "
            f"p={p_repr}; "
            f"d=json.load(open(p,encoding='utf-8')); "
            f"{filter_stmt}; "
            "open(p,'w',encoding='utf-8').write(json.dumps(d,indent=2)+'\\n') "
            "if d['tasks'] else os.remove(p); "
            "not d.get('tasks') and os.path.isdir(os.path.dirname(p)) "
            "and not os.listdir(os.path.dirname(p)) and os.rmdir(os.path.dirname(p))"
        )
    else:
        # Pre-existing file: always rewrite (preserving other top-level keys).
        py_script = (
            "import json, os; "
            f"p={p_repr}; "
            f"d=json.load(open(p,encoding='utf-8')); "
            f"{filter_stmt}; "
            "open(p,'w',encoding='utf-8').write(json.dumps(d,indent=2)+'\\n')"
        )

    # Escape py_script for safe embedding in the double-quoted -c "..." arg.
    # Without this, $ and ` in paths (from repr() output) would trigger
    # shell variable expansion / command substitution.
    if platform.system() == "Windows":
        # PowerShell double-quoted strings: backtick is the escape char.
        # Order matters: escape backticks first so they don't interact with
        # the backtick-escapes we add for $ and " in subsequent steps.
        py_script = py_script.replace("`", "``")
        py_script = py_script.replace("$", "`$")
        py_script = py_script.replace('"', '`"')
    else:
        # Bash double-quoted strings: backslash is the escape char.
        # Escape \ first (so existing backslashes don't interact with our
        # new \$ and \` escapes), then $ and ` which trigger expansion.
        py_script = py_script.replace("\\", "\\\\")
        py_script = py_script.replace("$", "\\$")
        py_script = py_script.replace("`", "\\`")
        py_script = py_script.replace('"', '\\"')

    return f'{python_cmd} -c "{py_script}"'


def _remove_stale_auto_start_task(
    tasks_path: str,
    vscode_dir: str,
    task_label: str,
) -> None:
    """Best-effort remove a stale auto-start task from ``tasks.json``.

    Called when the sentinel file already exists, indicating a previous run
    succeeded but its cleanup may have failed.  If the task is found and
    removed:

    * When other tasks remain the file is rewritten.
    * When no tasks remain **and** the file has no other top-level keys
      besides ``version`` and ``tasks``, the file is **deleted** and
      ``.vscode/`` is removed if empty.
    * When no tasks remain but other top-level keys exist (e.g. ``inputs``,
      ``options``), the file is rewritten preserving those keys.

    All errors are silently caught so this never prevents the caller from
    proceeding.
    """
    if not os.path.isfile(tasks_path):
        return
    try:
        with open(tasks_path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return
        tasks_list = data.get("tasks")
        if not isinstance(tasks_list, list):
            return
        original_count = len(tasks_list)
        data["tasks"] = [t for t in tasks_list if not isinstance(t, dict) or t.get("label") != task_label]
        if len(data["tasks"]) == original_count:
            return  # Task was not present — nothing to clean up
        if data["tasks"]:
            # Other tasks remain — rewrite the file.
            with open(tasks_path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(data, indent=2) + "\n")
        else:
            # No tasks remain.  Only delete the file when it contains no
            # other top-level keys besides ``version`` and ``tasks`` (i.e.
            # it was likely created solely for auto-start).  If other keys
            # exist (e.g. ``inputs``, ``options``) the file belongs to the
            # user — rewrite it preserving those keys.
            extra_keys = set(data.keys()) - {"version", "tasks"}
            if extra_keys:
                with open(tasks_path, "w", encoding="utf-8") as fh:
                    fh.write(json.dumps(data, indent=2) + "\n")
            else:
                os.remove(tasks_path)
                try:
                    os.rmdir(vscode_dir)
                except OSError:
                    pass
    except (json.JSONDecodeError, OSError):
        pass  # Best-effort — silently ignore errors


def inject_auto_start_task(
    worktree_path: str,
    command: List[str],
    task_label: str = _AUTO_START_TASK_LABEL,
) -> bool:
    """Write a ``.vscode/tasks.json`` task that auto-runs when the folder opens.

    The task is configured with ``"runOn": "folderOpen"`` so that VS Code
    executes the *command* in the integrated terminal immediately when the
    workspace window opens.  The task also checks for a sentinel file
    (``.agdt/.copilot-auto-start-triggered``) and exits early if it exists,
    preventing re-execution on subsequent window opens.  After the command
    finishes **successfully** the task cleans up by removing itself from
    ``tasks.json``.  When ``tasks.json`` did not exist before injection and
    no other tasks remain, the file (and the ``.vscode/`` directory if
    empty) is **deleted** so no untracked files are left behind.  When
    ``tasks.json`` was pre-existing the file is rewritten (preserving
    other top-level keys such as ``inputs`` or ``options``).  On failure
    the task remains in ``tasks.json`` so the next ``folderOpen`` retries
    the command.

    The function merges the new task into an existing ``tasks.json`` if one
    is present, preserving any user-defined tasks.

    This is a **no-op** when ``is_vscode_available()`` returns ``False``.

    Args:
        worktree_path: Absolute path to the worktree directory.
        command: The command to execute, as a list of strings (e.g.
            ``["copilot", "-i", "prompt text"]``).
        task_label: Label for the injected task (default:
            ``"agdt-copilot-auto-start"``).  Used to identify the task
            during cleanup.

    Returns:
        ``True`` if the task was written successfully, ``False`` otherwise
        (e.g. VS Code not available, filesystem errors).
    """
    if not is_vscode_available():
        return False

    # Validate that the command list is non-empty and contains only strings.
    if not command or not all(isinstance(c, str) for c in command):
        return False

    vscode_dir = os.path.join(worktree_path, ".vscode")
    tasks_path = os.path.join(vscode_dir, "tasks.json")
    sentinel_path = os.path.join(worktree_path, ".agdt", ".copilot-auto-start-triggered")

    # Skip injection when the sentinel already exists — the command was
    # already executed successfully in a previous window open.  Without
    # this guard the task would be written but then exit immediately in
    # the sentinel short-circuit, leaving an orphaned entry in tasks.json.
    if os.path.exists(sentinel_path):
        # Best-effort cleanup: remove any stale auto-start task that may
        # have been left behind from a previous run whose cleanup failed
        # or was interrupted.  This prevents the orphaned task entry from
        # persisting permanently in tasks.json.
        _remove_stale_auto_start_task(tasks_path, vscode_dir, task_label)
        return False

    # --- Read existing tasks.json (if any) -----------------------------------
    tasks_config: dict = {"version": "2.0.0", "tasks": []}
    file_existed = os.path.exists(tasks_path)
    if file_existed:
        try:
            with open(tasks_path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            # Guard: a valid tasks.json could be any JSON type; treat
            # non-dict top-levels as malformed and overwrite.
            if isinstance(loaded, dict):
                tasks_config = loaded
                # Ensure the required ``version`` field is present so VS Code
                # will accept the file even if the existing one was missing it.
                tasks_config.setdefault("version", "2.0.0")
            else:
                print(
                    f"Warning: {tasks_path} is not a JSON object — will overwrite",
                    file=sys.stderr,
                )
        except (json.JSONDecodeError, OSError) as exc:
            print(
                f"Warning: could not read {tasks_path}: {exc} — will overwrite",
                file=sys.stderr,
            )

    # Ensure the tasks list exists
    if "tasks" not in tasks_config or not isinstance(tasks_config.get("tasks"), list):
        tasks_config["tasks"] = []

    # Remove any previously-injected task with the same label to avoid duplicates.
    # Guard with isinstance(t, dict) so non-dict items don't raise on .get().
    tasks_config["tasks"] = [
        t for t in tasks_config["tasks"] if not isinstance(t, dict) or t.get("label") != task_label
    ]

    # --- Build the composite shell command -----------------------------------
    # The command: (1) checks sentinel, (2) creates sentinel, (3) runs the
    # user command, (4) on failure removes sentinel so next open retries,
    # (5) on success cleans up tasks.json (non-fatal), (6) exits with the
    # user command's exit code so VS Code reflects the correct status.
    #
    # Cleanup only runs on success so that a failed command leaves the task
    # in tasks.json — the sentinel was already removed (step 4), so the
    # next ``folderOpen`` will retry the task.
    sentinel_unix = sentinel_path.replace("\\", "/")
    cleanup_cmd = _build_cleanup_shell_command(worktree_path, task_label, created_new=not file_existed)

    if platform.system() == "Windows":
        # PowerShell syntax
        sentinel_win = sentinel_path.replace("/", "\\")
        sentinel_dir_win = os.path.dirname(sentinel_win)
        # Always single-quote every arg so PowerShell metacharacters
        # (;  &  |  >  etc.) are treated as literals.
        # Escape embedded single quotes via PowerShell's '' convention.
        quoted_parts = []
        for part in command:
            escaped = part.replace("'", "''")
            quoted_parts.append(f"'{escaped}'")
        cmd_str = "& " + " ".join(quoted_parts)
        # Also escape single quotes in sentinel paths for safe embedding.
        sentinel_win_safe = sentinel_win.replace("'", "''")
        sentinel_dir_win_safe = sentinel_dir_win.replace("'", "''")
        shell_command = (
            f"if (Test-Path -LiteralPath '{sentinel_win_safe}') {{ exit 0 }}; "
            f"New-Item -ItemType Directory -Force -LiteralPath '{sentinel_dir_win_safe}' | Out-Null; "
            f"New-Item -ItemType File -Force -LiteralPath '{sentinel_win_safe}' | Out-Null; "
            f"{cmd_str}; "
            f"$agdtExit=$LASTEXITCODE; "
            f"if ($agdtExit -ne 0) {{ Remove-Item -LiteralPath "
            f"'{sentinel_win_safe}' -Force -ErrorAction SilentlyContinue }}; "
            f"if ($agdtExit -eq 0) {{ try {{ {cleanup_cmd} }} catch {{}} }}; "
            f"exit $agdtExit"
        )
    else:
        # Bash syntax
        import shlex

        cmd_str = shlex.join(command)
        sentinel_dir_unix = os.path.dirname(sentinel_unix)
        # Use shlex.quote() for sentinel paths so that $, backticks, etc.
        # in worktree paths are not expanded by the shell.
        sentinel_q = shlex.quote(sentinel_unix)
        sentinel_dir_q = shlex.quote(sentinel_dir_unix)
        shell_command = (
            f"if [ -f {sentinel_q} ]; then exit 0; fi; "
            f"mkdir -p {sentinel_dir_q}; "
            f"touch {sentinel_q}; "
            f"{cmd_str}; "
            f"agdt_exit=$?; "
            f"if [ $agdt_exit -ne 0 ]; then rm -f {sentinel_q}; fi; "
            f"if [ $agdt_exit -eq 0 ]; then {cleanup_cmd} || true; fi; "
            f"exit $agdt_exit"
        )

    # --- Build the task definition -------------------------------------------
    task_def = {
        "label": task_label,
        "type": "shell",
        "command": shell_command,
        "runOptions": {"runOn": "folderOpen"},
        "presentation": {
            "reveal": "always",
            "focus": True,
        },
        "problemMatcher": [],
    }

    # On Windows, explicitly use PowerShell to avoid relying on the user's
    # default shell (which may be cmd.exe or Git Bash).
    if platform.system() == "Windows":
        task_def["options"] = {
            "shell": {
                "executable": "powershell.exe",
                "args": ["-Command"],
            }
        }

    tasks_config["tasks"].append(task_def)

    # --- Write tasks.json ----------------------------------------------------
    try:
        os.makedirs(vscode_dir, exist_ok=True)
        with open(tasks_path, "w", encoding="utf-8") as fh:
            json.dump(tasks_config, fh, indent=2)
            fh.write("\n")
        print(f"Injected auto-start task '{task_label}' into {tasks_path}")
        return True
    except OSError as exc:
        print(f"Warning: could not write {tasks_path}: {exc}", file=sys.stderr)
        return False


def run_worktree_setup_script(worktree_path: str) -> None:
    """
    Run the project-specific worktree setup script if it exists.

    Looks for ``.agdt/agentic-devtools-worktree-setup.py`` in the worktree
    root.  If found, executes it using the current Python interpreter with the
    worktree root passed as the first argument and the worktree root set as the
    working directory.  If the script is absent, returns silently.  Execution
    errors are logged as warnings but do not raise.

    Security: symlinks are rejected and the resolved script path must remain
    inside the worktree root to guard against malicious repos using symlinks to
    point the setup script at arbitrary files outside the worktree.

    Args:
        worktree_path: Path to the worktree directory.
    """
    worktree_root = Path(worktree_path).resolve()
    script_path = worktree_root / ".agdt" / "agentic-devtools-worktree-setup.py"

    if not (script_path.is_file() and os.access(str(script_path), os.R_OK)):
        return

    # Security: reject symlinks or scripts that resolve outside the worktree.
    try:
        if script_path.is_symlink():
            print(
                f"Warning: refusing to execute symlinked worktree setup script: {script_path}",
                file=sys.stderr,
            )
            return

        resolved_script_path = script_path.resolve()
        try:
            resolved_script_path.relative_to(worktree_root)
        except ValueError:
            print(
                f"Warning: refusing to execute worktree setup script outside worktree: {resolved_script_path}",
                file=sys.stderr,
            )
            return
    except OSError as exc:
        print(f"Warning: could not validate worktree setup script path: {exc}", file=sys.stderr)
        return

    print(f"Running worktree setup script: {resolved_script_path}")
    try:
        result = subprocess.run(
            [sys.executable, str(resolved_script_path), str(worktree_root)],
            cwd=str(worktree_root),
            check=False,
        )
        if result.returncode != 0:
            print(
                f"Warning: worktree setup script exited with code {result.returncode}",
                file=sys.stderr,
            )
        else:
            print("Worktree setup script completed successfully.")
    except (FileNotFoundError, OSError) as exc:
        print(f"Warning: could not run worktree setup script: {exc}", file=sys.stderr)


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
    2. Injects ``.vscode/settings.json`` with Git for Windows PATH entries (Windows only)
    3. Runs ``.agdt/agentic-devtools-worktree-setup.py`` if present
    4. Opens VS Code with the workspace file

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

    # Step 2: Inject VS Code settings for Windows Git PATH
    inject_git_path_settings(result.worktree_path)

    # Step 3: Run project-specific worktree setup script if present
    run_worktree_setup_script(result.worktree_path)

    # Step 4: Open VS Code
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
        "apply-pull-request-review-suggestions": "agdt-initiate-apply-pr-suggestions-workflow",
        "create-jira-issue": "agdt-initiate-create-jira-issue-workflow",
        "create-jira-epic": "agdt-initiate-create-jira-epic-workflow",
        "create-jira-subtask": "agdt-initiate-create-jira-subtask-workflow",
        "update-jira-issue": "agdt-initiate-update-jira-issue-workflow",
        "optimize-issue-for-ai-agent": "agdt-initiate-optimize-issue-for-ai-agent-workflow",
        "break-down-issue-into-subtasks": "agdt-initiate-break-down-issue-into-subtasks-workflow",
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
📋 WORKFLOW CONTINUATION
================================================================================

A Copilot session will start automatically in the new VS Code window.
If the session doesn't start, paste this command in the VS Code AI chat:

```
{full_command}
```

This command is a fallback — normally the session starts automatically.
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
        "apply-pull-request-review-suggestions": "agdt-initiate-apply-pr-suggestions-workflow",
        "create-jira-issue": "agdt-initiate-create-jira-issue-workflow",
        "create-jira-epic": "agdt-initiate-create-jira-epic-workflow",
        "create-jira-subtask": "agdt-initiate-create-jira-subtask-workflow",
        "update-jira-issue": "agdt-initiate-update-jira-issue-workflow",
        "optimize-issue-for-ai-agent": "agdt-initiate-optimize-issue-for-ai-agent-workflow",
        "break-down-issue-into-subtasks": "agdt-initiate-break-down-issue-into-subtasks-workflow",
    }

    base_command = workflow_base_commands.get(workflow_name, "agdt-initiate-work-on-jira-issue-workflow")

    # Build the full command with parameters
    # For PR-based workflows, use --pull-request-id instead of --issue-key
    if (
        workflow_name in ("pull-request-review", "apply-pull-request-review-suggestions")
        and additional_params
        and additional_params.get("pull_request_id")
    ):
        pull_request_id = additional_params["pull_request_id"]
        command_parts = [base_command, f"--pull-request-id {pull_request_id}"]
    else:
        command_parts = [base_command, f"--issue-key {issue_key}"]

    if user_request:  # pragma: no cover
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
    elif workflow_name == "apply-pull-request-review-suggestions":
        task_description = "assigned to apply pull request review suggestions"
        action_description = "apply the PR review suggestions to the codebase as specified in the workflow prompt"
    elif workflow_name == "optimize-issue-for-ai-agent":
        task_description = "assigned to optimize a Jira issue for AI-agent clarity"
        action_description = (
            "rewrite the Jira issue to be clear and actionable for an AI agent, "
            "then apply the update via agdt-update-jira-issue"
        )
    elif workflow_name == "break-down-issue-into-subtasks":
        task_description = "assigned to break down a Jira issue into subtasks"
        action_description = (
            "analyze the Jira issue and create subtasks via agdt-initiate-create-jira-subtask-workflow"
        )
    else:
        task_description = "assigned an issue to work on"
        action_description = "work on the issue until you have completed the workflow"

    return f"""NOTE: A Copilot session should start automatically in the VS Code integrated terminal. \
The instructions below are a fallback in case the auto-start did not succeed.

You are a senior software engineer and expert architect who has been {task_description}.

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


def _run_auto_execute_command(
    command: list[str],
    worktree_path: str,
    timeout: int,
) -> int:
    """
    Execute a command inside a worktree and log the output.

    Args:
        command: The command and arguments to run.
        worktree_path: The working directory for the command.
        timeout: Maximum seconds to wait for the command.

    Returns:
        The process exit code, or -1 if the command could not be started or timed out.
    """
    print(f"\n--- Executing command in worktree: {' '.join(command)} ---")
    # Inherit current environment and pin AGENTIC_DEVTOOLS_STATE_DIR to the
    # target worktree's identity-scoped state directory when the bootstrap
    # file contains both ``identity`` and ``worktree_key``.  Falls back to
    # ``_unscoped`` when the bootstrap file is missing, unreadable, or
    # malformed, when either key is absent or empty, or when either segment
    # fails ``is_safe_dir_segment()`` validation.  This propagates into
    # any nested background tasks spawned by the auto-execute command so
    # that prompt files and state are written to the correct worktree location
    # instead of falling back to a Python-install-relative temp directory.
    env = os.environ.copy()

    # Read bootstrap file to resolve identity-scoped state directory
    bootstrap_path = Path(worktree_path) / ".agdt" / "runtime-bootstrap.json"
    identity = ""
    worktree_key = ""
    try:
        if bootstrap_path.is_file():
            data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw_id = data.get("identity", "")
                raw_wk = data.get("worktree_key", "")
                identity = raw_id.strip() if isinstance(raw_id, str) else ""
                worktree_key = raw_wk.strip() if isinstance(raw_wk, str) else ""
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        pass

    # Validate that identity/worktree_key are safe single-component directory
    # names (no path separators, no ``..``) to prevent the state dir from
    # escaping the .agdt/workflows subtree via a malformed bootstrap file.
    from ...state import is_safe_dir_segment

    if identity and worktree_key and is_safe_dir_segment(identity) and is_safe_dir_segment(worktree_key):
        state_dir = Path(worktree_path) / ".agdt" / "workflows" / identity / worktree_key
    else:
        if identity and worktree_key:
            # Both values present but at least one failed safety validation.
            print(
                f"WARNING: unsafe bootstrap identity/worktree_key "
                f"({identity!r}/{worktree_key!r}), falling back to _unscoped"
            )
        state_dir = Path(worktree_path) / ".agdt" / "workflows" / "_unscoped"
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"WARNING: Failed to create state directory {state_dir!s}: {e}")
    env["AGENTIC_DEVTOOLS_STATE_DIR"] = str(state_dir)

    try:
        exec_result = subprocess.run(
            command,
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # Security: no shell expansion
            env=env,
        )
        if exec_result.stdout:
            print(exec_result.stdout)
        if exec_result.returncode != 0:
            print(f"WARNING: Command exited with code {exec_result.returncode}")
            if exec_result.stderr:
                print(exec_result.stderr)
        return exec_result.returncode
    except subprocess.TimeoutExpired:
        print(f"WARNING: Command timed out after {timeout} seconds")
        return -1
    except (FileNotFoundError, OSError) as e:
        print(f"WARNING: Command failed to execute: {e}")
        return -1


def _wait_for_prompt_file(
    prompt_path: Path,
    timeout: float = 300,
    poll_interval: float = 5.0,
) -> bool:
    """
    Poll for a prompt file to appear on disk.

    The file may be written by a background process started by the
    auto-execute command, so we wait up to *timeout* seconds for it
    to be created.

    Args:
        prompt_path: Absolute path to the expected prompt file.
        timeout: Maximum seconds to wait (default: 300; accepts fractional seconds).
        poll_interval: Seconds between checks (default: 5).

    Returns:
        True when the file exists; False if the timeout was reached.
    """
    import time

    elapsed = 0.0
    while elapsed < timeout:
        if prompt_path.exists():
            return True
        time.sleep(poll_interval)
        elapsed += poll_interval
    return prompt_path.exists()


def _start_copilot_session_for_workflow(
    worktree_path: str,
    prompt_file_relative_path: str,
    start_prompt: str,
    workflow_name: str,
    interactive: bool = False,
) -> bool:
    """Wait for the workflow setup to complete, then start a ``gh copilot`` session.

    This is the generic helper that all workflow-specific wrappers delegate
    to.  It waits for a prompt file to appear on disk, detects VS Code /
    TTY availability, handles the auto-start task sentinel check, and
    finally calls :func:`start_copilot_session`.

    **Auto-start task handling**: The VS Code auto-start task is injected
    *before* VS Code opens (by :func:`_maybe_inject_auto_start_before_vscode`
    in the background worktree setup flow).  When this function detects the
    task was already injected and there is no TTY attached (background task
    scenario), it waits for the sentinel file to confirm VS Code handled the
    session.  This check runs regardless of the *interactive* flag — injection
    is attempted whenever VS Code is available (even when the background setup
    was invoked with ``interactive=False``).

    In interactive mode the Copilot session inherits the terminal so the
    user can interact with it; in non-interactive mode it runs in the
    background (pipeline use-case).

    When VS Code is not available the session is forced non-interactive
    regardless of the *interactive* argument.

    Args:
        worktree_path: Absolute path to the worktree root.
        prompt_file_relative_path: Path to the prompt file relative to
            *worktree_path* (forward-slash separated segments joined via
            ``Path(worktree_path) / prompt_file_relative_path``).
        start_prompt: The prompt text to pass to ``start_copilot_session()``.
        workflow_name: Human-readable workflow name for log messages.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started successfully or the
        VS Code auto-start task was confirmed running.  ``False`` when
        the prompt file was not found or was not a regular file.
    """
    from ..copilot.session import start_copilot_session

    prompt_file = Path(worktree_path) / prompt_file_relative_path

    print(f"\n--- Waiting for initiate prompt file ({workflow_name}): {prompt_file} ---")
    if not _wait_for_prompt_file(prompt_file):
        print("WARNING: Initiate prompt file not found after waiting. Skipping Copilot session.")
        return False
    if not prompt_file.is_file():
        print("WARNING: Initiate prompt path exists but is not a regular file. Skipping Copilot session.")
        return False

    # Non-interactive mode when VS Code is not available (pipeline scenario),
    # or when there is no TTY attached (e.g. running inside run_function_in_background
    # where stdin/stdout are redirected to DEVNULL/log files).
    has_tty = getattr(sys.stdin, "isatty", lambda: False)() and getattr(sys.stdout, "isatty", lambda: False)()

    # --- Check if the VS Code auto-start task was already injected -----------
    # _maybe_inject_auto_start_before_vscode() injects the task *before* VS
    # Code opens so that ``runOn: folderOpen`` fires with the task present.
    # When that happened and we're in a background context (no TTY), we wait
    # briefly for the sentinel file to confirm the VS Code task actually
    # started.  If the sentinel appears, VS Code is handling the session and
    # we can skip.  If it doesn't appear within a reasonable window (e.g.
    # VS Code failed to open or the task didn't fire), we fall through and
    # start the session ourselves as a fallback.
    # NOTE: The check intentionally does NOT require interactive=True.
    # Injection happens regardless of the interactive flag (see
    # _maybe_inject_auto_start_before_vscode), so we must check for the
    # auto-start task even when interactive=False.
    if not has_tty and is_vscode_available():
        tasks_path = os.path.join(worktree_path, ".vscode", "tasks.json")
        sentinel_path = os.path.join(worktree_path, ".agdt", ".copilot-auto-start-triggered")
        if os.path.exists(tasks_path):
            try:
                with open(tasks_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    tasks_list = data.get("tasks")
                    if not isinstance(tasks_list, list):
                        tasks_list = []
                    if any(isinstance(t, dict) and t.get("label") == _AUTO_START_TASK_LABEL for t in tasks_list):
                        # Check whether the sentinel already exists *before*
                        # we start waiting.  A pre-existing sentinel (e.g.
                        # left from a previous run) would cause the VS Code
                        # task to exit immediately without starting a session.
                        # In that case we must fall through to the background
                        # session so the user still gets a Copilot session.
                        if os.path.exists(sentinel_path):
                            print(
                                "\n--- Pre-existing sentinel detected. "
                                "VS Code task will skip; falling back to "
                                "background Copilot session. ---"
                            )
                        else:
                            print(
                                "\n--- VS Code auto-start task present. "
                                "Waiting for VS Code to start the Copilot session... ---"
                            )
                            # Wait up to 15 seconds for the sentinel file to appear,
                            # which means the VS Code task actually executed.
                            import time

                            _SENTINEL_WAIT_SECONDS = 15
                            _SENTINEL_POLL_INTERVAL = 1.0
                            waited = 0.0
                            while waited < _SENTINEL_WAIT_SECONDS:
                                if os.path.exists(sentinel_path):
                                    print(
                                        "--- VS Code auto-start task confirmed running. "
                                        "Copilot session is in the integrated terminal. ---"
                                    )
                                    return True
                                time.sleep(_SENTINEL_POLL_INTERVAL)
                                waited += _SENTINEL_POLL_INTERVAL
                            print(
                                "--- VS Code auto-start task did not fire within "
                                f"{_SENTINEL_WAIT_SECONDS}s. "
                                "Falling back to background Copilot session. ---"
                            )
            except (json.JSONDecodeError, OSError):
                pass  # Fall through to starting the session directly

    if not has_tty and not is_vscode_available():
        print(
            "NOTE: VS Code integrated terminal auto-start not available. "
            "Copilot session will run in the background. "
            "Run agdt-task-log to view output."
        )

    effective_interactive = interactive and is_vscode_available() and has_tty

    print(
        f"\n--- Starting gh copilot session for {workflow_name} "
        f"(mode: {'interactive' if effective_interactive else 'non-interactive'}) ---"
    )
    # Ensure Copilot session state and artifacts (prompt file, log file, copilot.*
    # state keys) are written under the target worktree, not the caller's CWD.
    # start_copilot_session() resolves paths via get_state_dir() which is CWD-based;
    # we temporarily override AGENTIC_DEVTOOLS_STATE_DIR and chdir to worktree_path
    # so that get_state_dir() resolves from the worktree's .agdt/runtime-bootstrap.json.
    previous_state_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
    previous_cwd = os.getcwd()
    try:
        # Unset the env var before calling get_state_dir() so it resolves from
        # the worktree context rather than honouring the caller's value.
        # Both the pop and chdir are inside the try so the finally block always
        # restores them even if os.chdir() raises (e.g. missing worktree_path).
        os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
        os.chdir(worktree_path)

        from ...state import get_state_dir

        state_dir = get_state_dir()
        os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = str(state_dir)
        start_copilot_session(
            prompt=start_prompt,
            working_directory=worktree_path,
            interactive=effective_interactive,
        )
        return True
    finally:
        os.chdir(previous_cwd)
        if previous_state_dir is None:
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
        else:
            os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = previous_state_dir


def _start_copilot_session_for_pr_review(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the pull-request-review workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies PR-review-specific parameters (prompt file path and start
    prompt text).

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(
            worktree_path, "temp-pull-request-review-initiate-prompt.md"
        ),
        start_prompt=COPILOT_SESSION_START_PROMPT,
        workflow_name="pull-request-review",
        interactive=interactive,
    )


def _prompt_file_relative_path(worktree_path: str, prompt_filename: str) -> str:
    """Resolve the prompt file path relative to *worktree_path*.

    The prompt file lives in the state directory (returned by
    :func:`get_state_dir`).  This helper computes the relative path from
    *worktree_path* so that ``_start_copilot_session_for_workflow`` can
    construct the absolute path via ``Path(worktree_path) / relative``.

    When ``AGENTIC_DEVTOOLS_STATE_DIR`` is already set *and* points to a
    directory under the target worktree, the env-var value is used directly.
    This is the path where prompt files were written by the auto-execute
    subprocess (see :func:`_run_auto_execute_command`), so using it ensures
    prompt generation and prompt lookup agree.  The containment check uses
    ``os.path.normcase`` so that drive-letter and path casing differences
    on Windows do not cause a false negative.

    When the env var is absent or points outside the worktree,
    ``get_state_dir()`` is resolved inside the *worktree* context
    (CWD + env override cleared) so the returned path points to the
    worktree's own state directory — not the caller's.
    """
    from ...state import get_state_dir

    # Fast path: honour AGENTIC_DEVTOOLS_STATE_DIR when it already points
    # under the target worktree — this is the path the auto-execute
    # subprocess used to write the prompt files.  Unsetting the env var and
    # resolving via bootstrap could yield a different (scoped) directory,
    # causing the session launcher to wait for a file that will never appear
    # at the bootstrap-resolved path.
    env_state_dir = os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR")
    if env_state_dir:
        try:
            real_env = os.path.normcase(os.path.realpath(env_state_dir))
            real_wt = os.path.normcase(os.path.realpath(worktree_path))
            if real_env == real_wt or real_env.startswith(real_wt + os.sep):
                state_dir = Path(env_state_dir)
                return os.path.relpath(str(state_dir / prompt_filename), worktree_path)
        except (OSError, ValueError):
            pass  # Fall through to bootstrap resolution

    # Slow path: resolve get_state_dir() in the worktree context.
    # Same pattern as _start_copilot_session_for_workflow() itself.
    previous_state_dir = env_state_dir
    previous_cwd = os.getcwd()
    try:
        os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
        os.chdir(worktree_path)
        state_dir = get_state_dir()
        return os.path.relpath(str(state_dir / prompt_filename), worktree_path)
    finally:
        os.chdir(previous_cwd)
        if previous_state_dir is None:
            os.environ.pop("AGENTIC_DEVTOOLS_STATE_DIR", None)
        else:
            os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = previous_state_dir


def _start_copilot_session_for_apply_pr_suggestions(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the apply-pull-request-review-suggestions workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies apply-pr-suggestions-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(
            worktree_path, "temp-apply-pull-request-review-suggestions-initiate-prompt.md"
        ),
        start_prompt=COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS,
        workflow_name="apply-pull-request-review-suggestions",
        interactive=interactive,
    )


def _start_copilot_session_for_work_on_jira_issue(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the work-on-jira-issue workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies work-on-jira-issue-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(
            worktree_path, "temp-work-on-jira-issue-planning-prompt.md"
        ),
        start_prompt=COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE,
        workflow_name="work-on-jira-issue",
        interactive=interactive,
    )


def _start_copilot_session_for_create_jira_issue(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the create-jira-issue workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies create-jira-issue-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(
            worktree_path, "temp-create-jira-issue-initiate-prompt.md"
        ),
        start_prompt=COPILOT_SESSION_START_PROMPT_CREATE_JIRA_ISSUE,
        workflow_name="create-jira-issue",
        interactive=interactive,
    )


def _start_copilot_session_for_create_jira_epic(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the create-jira-epic workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies create-jira-epic-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(worktree_path, "temp-create-jira-epic-initiate-prompt.md"),
        start_prompt=COPILOT_SESSION_START_PROMPT_CREATE_JIRA_EPIC,
        workflow_name="create-jira-epic",
        interactive=interactive,
    )


def _start_copilot_session_for_create_jira_subtask(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the create-jira-subtask workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies create-jira-subtask-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(
            worktree_path, "temp-create-jira-subtask-initiate-prompt.md"
        ),
        start_prompt=COPILOT_SESSION_START_PROMPT_CREATE_JIRA_SUBTASK,
        workflow_name="create-jira-subtask",
        interactive=interactive,
    )


def _start_copilot_session_for_update_jira_issue(
    worktree_path: str,
    interactive: bool = False,
) -> bool:
    """Start a Copilot session for the update-jira-issue workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies update-jira-issue-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.

    Returns:
        ``True`` when a Copilot session was started or the auto-start task
        confirmed running, ``False`` otherwise.
    """
    return _start_copilot_session_for_workflow(
        worktree_path=worktree_path,
        prompt_file_relative_path=_prompt_file_relative_path(
            worktree_path, "temp-update-jira-issue-initiate-prompt.md"
        ),
        start_prompt=COPILOT_SESSION_START_PROMPT_UPDATE_JIRA_ISSUE,
        workflow_name="update-jira-issue",
        interactive=interactive,
    )


def _maybe_inject_auto_start_before_vscode(
    worktree_path: str,
    start_prompt: str = COPILOT_SESSION_START_PROMPT,
) -> bool:
    """Inject a VS Code auto-start task before VS Code opens.

    Called right before ``open_vscode_workspace()`` so the task exists when
    the ``folderOpen`` event fires.  Uses *start_prompt* to tell the Copilot
    agent which workflow to execute — callers should pass the correct
    workflow-specific prompt (see :data:`_WORKFLOW_START_PROMPTS`).

    Injection is attempted regardless of the ``interactive`` flag passed to
    the outer worktree-setup flow.  Internal guards (``is_vscode_available()``,
    sentinel file check, etc.) prevent inappropriate injection.

    This is a best-effort helper: if ``build_copilot_args()`` returns
    ``None`` (Copilot CLI not found) or ``inject_auto_start_task()`` fails,
    the caller silently continues without the auto-start task; the existing
    fallback behaviour in the workflow-specific session launcher will
    handle the session.

    Returns:
        ``True`` if the auto-start task was successfully written to
        ``tasks.json``, ``False`` otherwise.
    """
    from ..copilot import build_copilot_args

    copilot_args = build_copilot_args(start_prompt, interactive=True)
    if copilot_args is not None:
        injected = inject_auto_start_task(worktree_path, copilot_args)
        if injected:
            print("   VS Code auto-start task injected (will run on window open).")
        return injected
    return False


def setup_worktree_in_background_sync(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: Optional[str] = None,
    use_existing_branch: bool = False,
    workflow_name: str = "work-on-jira-issue",
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
    auto_execute_command: Optional[list[str]] = None,
    auto_execute_timeout: int = 300,
    interactive: bool = False,
) -> None:
    """
    Perform worktree setup synchronously (called from background task).

    This function is designed to be called from a background task runner.
    It performs the full worktree setup and prints the continuation prompt.

    For ``pull-request-review`` workflows with an ``auto_execute_command``,
    the auto-execute command re-runs the full workflow inside the worktree,
    which handles starting the Copilot session itself.

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
        auto_execute_command: Optional command to run inside the worktree after
            creation. If the command fails, the error is logged but setup continues.
        auto_execute_timeout: Timeout in seconds for the auto-execute command
            (default: 300).
        interactive: Whether to start the Copilot session interactively after
            setup (default: False). Set to True for interactive mode.
    """
    from ...state import set_value

    print(f"\n{'=' * 80}")
    print("BACKGROUND WORKTREE SETUP")
    print("=" * 80)

    # Check if worktree already exists
    existing_path = check_worktree_exists(issue_key)
    if existing_path:
        print(f"\nWorktree already exists at: {existing_path}")
        print("Opening VS Code in the existing worktree (using the workspace file if available)...")

        # Inject VS Code auto-start task *before* opening the window so that
        # the ``runOn: folderOpen`` event fires with the task already present.
        wf_prompt = _WORKFLOW_START_PROMPTS.get(workflow_name, _WORKFLOW_AGNOSTIC_FALLBACK_PROMPT)
        _maybe_inject_auto_start_before_vscode(existing_path, start_prompt=wf_prompt)

        # Open VS Code
        vscode_opened = open_vscode_workspace(existing_path)
        print(f"   VS Code opened: {'Yes' if vscode_opened else 'No'}")

        if auto_execute_command:
            exit_code = _run_auto_execute_command(auto_execute_command, existing_path, auto_execute_timeout)
            set_value("worktree_setup.auto_execute_exit_code", str(exit_code))

        print("\n✅ Environment ready!")
        print(get_worktree_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("\n" + "=" * 80)
        print("AI AGENT INSTRUCTIONS (FALLBACK)")
        print("=" * 80)
        print("""
A Copilot session was started automatically in the VS Code integrated terminal.
The prompt below is a fallback — only provide it to the user if the auto-session did not start:
""")
        print("--- BEGIN PROMPT FOR USER TO COPY ---")
        print(get_ai_agent_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("--- END PROMPT FOR USER TO COPY ---")
        return

    # Create new worktree environment
    print(f"\nCreating worktree for issue {issue_key}...")
    if use_existing_branch and branch_name:  # pragma: no cover
        print(f"   Using existing branch from origin: {branch_name}")

    result = setup_worktree_environment(
        issue_key=issue_key,
        branch_prefix=branch_prefix,
        branch_name=branch_name,
        use_existing_branch=use_existing_branch,
        open_vscode=False,
    )

    if result.success:
        # Inject VS Code auto-start task *before* opening the window so that
        # the ``runOn: folderOpen`` event fires with the task already present.
        wf_prompt = _WORKFLOW_START_PROMPTS.get(workflow_name, _WORKFLOW_AGNOSTIC_FALLBACK_PROMPT)
        _maybe_inject_auto_start_before_vscode(result.worktree_path, start_prompt=wf_prompt)

        # Open VS Code after task injection
        result.vscode_opened = open_vscode_workspace(result.worktree_path)

        if auto_execute_command:
            exit_code = _run_auto_execute_command(auto_execute_command, result.worktree_path, auto_execute_timeout)
            set_value("worktree_setup.auto_execute_exit_code", str(exit_code))

        print("\n✅ Environment setup complete!")
        print(f"   Worktree: {result.worktree_path}")
        print(f"   Branch: {result.branch_name}")
        print(f"   VS Code opened: {'Yes' if result.vscode_opened else 'No'}")
        print(get_worktree_continuation_prompt(issue_key, workflow_name, user_request, additional_params))
        print("\n" + "=" * 80)
        print("AI AGENT INSTRUCTIONS (FALLBACK)")
        print("=" * 80)
        print("""
A Copilot session was started automatically in the VS Code integrated terminal.
The prompt below is a fallback — only provide it to the user if the auto-session did not start:
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
    auto_execute_command_str = get_value("worktree_setup.auto_execute_command")
    auto_execute_timeout_str = get_value("worktree_setup.auto_execute_timeout")
    interactive_str = get_value("worktree_setup.interactive")

    additional_params = None
    if additional_params_str:
        try:
            additional_params = json.loads(additional_params_str)
        except json.JSONDecodeError:
            pass

    auto_execute_command = None
    if auto_execute_command_str:
        try:
            auto_execute_command = json.loads(auto_execute_command_str)
        except json.JSONDecodeError:
            pass

    auto_execute_timeout = 300
    if auto_execute_timeout_str:
        try:
            auto_execute_timeout = int(auto_execute_timeout_str)
        except ValueError:
            pass

    # Default interactive to False; stored as "true" string to enable
    interactive = interactive_str == "true"

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
        auto_execute_command=auto_execute_command,
        auto_execute_timeout=auto_execute_timeout,
        interactive=interactive,
    )


def start_worktree_setup_background(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: Optional[str] = None,
    use_existing_branch: bool = False,
    workflow_name: str = "work-on-jira-issue",
    user_request: Optional[str] = None,
    additional_params: Optional[dict] = None,
    auto_execute_command: Optional[list[str]] = None,
    auto_execute_timeout: int = 300,
    interactive: bool = False,
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
        auto_execute_command: Optional command to run inside the worktree after
            creation. Passed through to setup_worktree_in_background_sync.
        auto_execute_timeout: Timeout in seconds for the auto-execute command
            (default: 300).
        interactive: Whether to start the Copilot session interactively after
            setup (default: False). Set to True for interactive mode.

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
    if branch_name:  # pragma: no cover
        set_value("worktree_setup.branch_name", branch_name)
    if use_existing_branch:  # pragma: no cover
        set_value("worktree_setup.use_existing_branch", "true")
    if user_request:
        set_value("worktree_setup.user_request", user_request)
    if additional_params:
        set_value("worktree_setup.additional_params", json.dumps(additional_params))
    if auto_execute_command:
        set_value("worktree_setup.auto_execute_command", json.dumps(auto_execute_command))
    if auto_execute_timeout != 300:
        set_value("worktree_setup.auto_execute_timeout", str(auto_execute_timeout))
    set_value("worktree_setup.interactive", "true" if interactive else "false")

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
