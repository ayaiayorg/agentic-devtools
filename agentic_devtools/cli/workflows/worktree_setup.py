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

from agentic_devtools.cli.vscode_tasks import remove_auto_start_task
from agentic_devtools.state import BOOTSTRAP_FILENAME, IDENTITY_CACHE_FILENAME

# Exported for dynamic invocation by run_function_in_background
__all__ = ["_setup_worktree_from_state"]

# ---------------------------------------------------------------------------
# Copilot-safe prompt design best practices
# ---------------------------------------------------------------------------
# - Do NOT use "CRITICAL", "WARNING", "DANGER", or similar alarm words; Copilot
#   CLI interprets these as unsafe and may halt execution.
# - Do NOT use "--- " separator dashes; they can be misinterpreted as unsafe
#   directive markers.
# - Use direct, actionable language, e.g. "Please run this command now:".
# - Avoid excessive emphasis (all-caps, bold, emojis) unless essential.
# - Each prompt MUST remain a single line (no ``\n``) and contain no template
#   variables (no ``{{`` / ``}}``).
# ---------------------------------------------------------------------------

# Static single-line prompt used when starting the Copilot CLI session for PR
# review.  It references the ``@agdt.advance-workflow`` agent so that Copilot
# advances to the pull-request-overview step via a trusted handoff instead of
# running a raw shell command.  The workflow is already initiated by the time
# this prompt is used, so we advance rather than re-initiate.
COPILOT_SESSION_START_PROMPT = (
    "You are a senior software engineer reviewing a Pull Request. "
    "Please hand off to @agdt.advance-workflow to advance to the pull-request-overview step. "
    "This agent will provide you with all PR details, review criteria, and instructions. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)

# ---------------------------------------------------------------------------
# Workflow-specific Copilot session start prompts
# Each MUST remain a single line (no ``\n``) and contain no template variables.
# ---------------------------------------------------------------------------

COPILOT_SESSION_START_PROMPT_APPLY_PR_SUGGESTIONS = (
    "You are applying pull request review suggestions. "
    "Please hand off to @agdt.get-next-workflow-prompt to display the current workflow step prompt. "
    "This agent will load the rendered prompt file containing full instructions "
    "on which review suggestions to apply and how. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)


COPILOT_SESSION_START_PROMPT_WORK_ON_JIRA_ISSUE = (
    "Please hand off to @agdt.get-next-workflow-prompt to display the work-on-jira-issue workflow instructions. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_CREATE_JIRA_ISSUE = (
    "Please hand off to @agdt.get-next-workflow-prompt to display the create-jira-issue workflow instructions. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_CREATE_JIRA_EPIC = (
    "Please hand off to @agdt.get-next-workflow-prompt to display the create-jira-epic workflow instructions. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_CREATE_JIRA_SUBTASK = (
    "Please hand off to @agdt.get-next-workflow-prompt to display the create-jira-subtask workflow instructions. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)

COPILOT_SESSION_START_PROMPT_UPDATE_JIRA_ISSUE = (
    "Please hand off to @agdt.get-next-workflow-prompt to display the update-jira-issue workflow instructions. "
    "Wait to begin any work until the handoff is complete. "
    "The agentic-devtools workflow will guide you through each step."
)

# Workflow-agnostic fallback prompt used when ``workflow_name`` is not found in
# ``_WORKFLOW_START_PROMPTS``.  This instructs the agent to hand off to the
# generic ``@agdt.get-next-workflow-prompt`` agent which re-renders the current
# step regardless of the specific workflow, so it's always safe to use as a
# default.
_WORKFLOW_AGNOSTIC_FALLBACK_PROMPT = (
    "Please hand off to @agdt.get-next-workflow-prompt to retrieve the current workflow instructions. "
    "Wait to begin any work until the handoff is complete. "
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

# Mapping from workflow name → prompt filename used by
# ``_start_copilot_session_for_workflow()`` to locate the rendered prompt
# file.  Extracted from the workflow-specific wrapper functions so that
# ``setup_worktree_in_background_sync()`` can call the generic session
# starter without importing the wrappers.
_WORKFLOW_PROMPT_FILENAMES: dict[str, str] = {
    "pull-request-review": "temp-pull-request-review-initiate-prompt.md",
    "apply-pull-request-review-suggestions": "temp-apply-pull-request-review-suggestions-initiate-prompt.md",
    "work-on-jira-issue": "temp-work-on-jira-issue-planning-prompt.md",
    "create-jira-issue": "temp-create-jira-issue-initiate-prompt.md",
    "create-jira-epic": "temp-create-jira-epic-initiate-prompt.md",
    "create-jira-subtask": "temp-create-jira-subtask-initiate-prompt.md",
    "update-jira-issue": "temp-update-jira-issue-initiate-prompt.md",
}


def _in_test_environment() -> bool:
    """Check if running inside a pytest session.

    Returns ``True`` when ``PYTEST_CURRENT_TEST`` is set in the
    environment.  Used as a guard in functions that launch VS Code
    windows or write ``tasks.json`` with ``runOn: folderOpen`` to
    prevent unexpected side-effects during test runs.

    The check is isolated in its own function so that tests which
    need to exercise the guarded logic can ``@patch`` it to return
    ``False`` while keeping the guard active for all other tests.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


def is_vscode_available() -> bool:
    """Check if VS Code CLI is available on PATH.

    Returns:
        True if the ``code`` command is found on PATH, False otherwise.
    """
    return shutil.which("code") is not None


def find_workspace_file(directory: str) -> str | None:
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
    parent_key: str | None = None,
) -> str:
    """
    Generate a branch name based on issue type and workflow.

    Patterns:
    - Create workflows: <issueType>/<issue_key>/create-<issueType>
    - Update workflows: <issueType>/<issue_key>/update-<issueType>
    - Subtask create: subtask/<parent_key>/<issue_key>/create-subtask

    Args:
        issue_key: The Jira issue key (e.g., "PROJECT-1234")
        issue_type: The issue type (Task, Epic, Sub-task, Bug, etc.)
        workflow_name: The workflow name (create-jira-issue, create-jira-epic, etc.)
        parent_key: For subtasks, the parent issue key (e.g., "PROJECT-1233")

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
    error_message: str | None = None
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
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        result_common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
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


def get_current_branch() -> str | None:
    """
    Get the current git branch name.

    Returns:
        The current branch name, or None if not in a git repo or detached HEAD.
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
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
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def get_main_repo_root() -> str | None:
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
            encoding="utf-8",
            errors="replace",
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


def get_repos_parent_dir() -> str | None:
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


def _propagate_agdt_cache(worktree_path: str, worktree_key: str | None = None) -> None:
    """Copy identity.json and runtime-bootstrap.json from the main repo into the new worktree.

    When *worktree_key* is provided, ``runtime-bootstrap.json`` is written with
    ``{"worktree_key": "<worktree_key>"}`` instead of being copied from the main
    repo, ensuring the worktree gets the correct key even if the main repo's
    bootstrap file has a stale value.

    Non-fatal: ``OSError`` and ``ValueError`` exceptions are logged to stderr
    and the worktree setup continues.  Both the temp-rename success path and
    the standard worktree creation success path call this helper to ensure
    consistent behaviour.
    """
    try:
        main_repo = get_main_repo_root()
        if not main_repo:
            return

        main_repo_path = Path(main_repo)
        src_identity = main_repo_path / ".agdt" / IDENTITY_CACHE_FILENAME
        src_bootstrap = main_repo_path / ".agdt" / BOOTSTRAP_FILENAME

        # If there is nothing to propagate and no explicit worktree_key override,
        # retain the previous no-op behaviour and avoid creating .agdt/ at all.
        if worktree_key is None and not src_identity.is_file() and not src_bootstrap.is_file():
            return

        dst_agdt = Path(worktree_path) / ".agdt"
        dst_agdt.mkdir(parents=True, exist_ok=True)

        # Best-effort copy of identity.json; failure here should not block
        # propagation of the runtime bootstrap file.
        if src_identity.is_file():
            shutil.copy2(str(src_identity), str(dst_agdt / IDENTITY_CACHE_FILENAME))

        # Propagate runtime-bootstrap.json so that the worktree resolves
        # to the correct scoped state directory. This is independent of
        # whether identity.json was present or successfully copied.
        dst_bootstrap = dst_agdt / BOOTSTRAP_FILENAME
        if worktree_key is not None:
            bootstrap_data = json.dumps({"worktree_key": worktree_key})
            dst_bootstrap.write_text(bootstrap_data, encoding="utf-8")
        elif src_bootstrap.is_file():
            shutil.copy2(str(src_bootstrap), str(dst_bootstrap))
    except (OSError, ValueError) as exc:
        print(
            f"Warning: failed to propagate AGDT cache (identity/bootstrap) to worktree: {exc}",
            file=sys.stderr,
        )


def create_worktree(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: str | None = None,
    use_existing_branch: bool = False,
) -> WorktreeSetupResult:
    """
    Create a git worktree for the given issue key.

    The worktree will be created as a sibling directory to the main repo,
    named after the issue key (e.g., ../PROJECT-1234).

    Args:
        issue_key: The issue key (e.g., "PROJECT-1234")
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
    import uuid
    from datetime import datetime, timezone

    from ..git.operations import (
        BranchSafetyCheckResult,
        check_branch_safe_to_recreate,
        delete_local_branch,
        fetch_branch,
        get_short_commit_hash,
        rename_local_branch,
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
            # Keep reused worktrees aligned with current scoped runtime bootstrap
            # so re-invocations do not fall back to _unscoped state.
            _propagate_agdt_cache(worktree_path, worktree_key=issue_key)
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

    current_branch = get_current_branch()
    in_worktree = is_in_worktree()

    # Check if we're currently on the target branch in the main repo.
    # Git doesn't allow creating a worktree for a branch that's already checked out.
    # For new-branch creation (not use_existing_branch), switch to main here.
    # For PR-review (use_existing_branch=True), the safety check below determines the
    # right strategy: unsafe branches use temp-rename (which frees the name without
    # needing a branch switch), while the SAFE path handles the switch just before
    # the worktree-add call.
    if current_branch == resolved_branch_name and not in_worktree and not use_existing_branch:
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
            status = safety_result.status

            # For BRANCH_NOT_ON_ORIGIN, check whether a local branch with this
            # name already exists.  Wrap the check in try/except so that an
            # environment problem (git missing, OS error) is treated as "no
            # local branch found" rather than crashing create_worktree().
            local_branch_exists = False
            if status == BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN:
                try:
                    local_branch_exists = (
                        subprocess.run(
                            ["git", "rev-parse", "--verify", branch_name],
                            capture_output=True,
                            encoding="utf-8",
                            errors="replace",
                            check=False,
                        ).returncode
                        == 0
                    )
                except (FileNotFoundError, OSError):
                    local_branch_exists = False

            # When UNCOMMITTED_CHANGES is reported, it refers to the current
            # branch (HEAD), which might not be the target branch for the
            # worktree. Resolve the current branch name so we only treat this
            # as local work on the target branch when the names match.
            current_branch_name: str | None = None
            if status == BranchSafetyCheckResult.UNCOMMITTED_CHANGES:
                current_branch_name = get_current_branch()

            # Determine if we need the temp-rename flow to preserve local work
            needs_temp_rename = (
                status == BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN
                or (status == BranchSafetyCheckResult.UNCOMMITTED_CHANGES and current_branch_name == branch_name)
                or (status == BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN and local_branch_exists)
            )

            if needs_temp_rename:
                temp_suffix = uuid.uuid4().hex[:8]
                temp_branch_name = f"{branch_name}-tmp-{temp_suffix}"

                print(f"Local branch '{branch_name}' has local work. Temporarily renaming to '{temp_branch_name}'...")
                try:
                    rename_ok = rename_local_branch(branch_name, temp_branch_name)
                except (FileNotFoundError, OSError) as exc:
                    return WorktreeSetupResult(
                        success=False,
                        worktree_path=worktree_path,
                        branch_name=resolved_branch_name,
                        error_message=(f"Failed to rename local branch '{branch_name}' to '{temp_branch_name}': {exc}"),
                    )
                if not rename_ok:
                    return WorktreeSetupResult(
                        success=False,
                        worktree_path=worktree_path,
                        branch_name=resolved_branch_name,
                        error_message=(f"Failed to rename local branch '{branch_name}' to '{temp_branch_name}'."),
                    )

                # Attempt worktree creation using the original branch name from origin
                try:
                    print(f"Creating worktree at {worktree_path}...")
                    worktree_result = subprocess.run(
                        [
                            "git",
                            "worktree",
                            "add",
                            worktree_path,
                            "--track",
                            "-b",
                            branch_name,
                            f"origin/{branch_name}",
                        ],
                        capture_output=True,
                        encoding="utf-8",
                        errors="replace",
                        check=False,
                    )
                except (FileNotFoundError, OSError) as e:
                    # Revert the rename before propagating the error.
                    # If the revert also fails, include the recovery command in the error message.
                    error_msg = f"Error creating worktree: {e}"
                    try:
                        revert_ok = rename_local_branch(temp_branch_name, branch_name)
                    except (FileNotFoundError, OSError) as rename_exc:
                        revert_ok = False
                        error_msg += f" (revert also failed: {rename_exc})"
                    if not revert_ok:
                        error_msg += (
                            f"\nWarning: Failed to revert branch rename. "
                            f"Branch is still named '{temp_branch_name}'. "
                            f"Manually rename it back with: git branch -m {temp_branch_name} {branch_name}"
                        )
                    return WorktreeSetupResult(
                        success=False,
                        worktree_path=worktree_path,
                        branch_name=resolved_branch_name,
                        error_message=error_msg,
                    )

                if worktree_result.returncode != 0:
                    # Worktree creation failed — revert temp rename to keep local work intact.
                    # If the revert also fails, include the recovery command in the error message.
                    print("Worktree creation failed. Reverting temp rename...")
                    error_msg = f"Failed to create worktree: {worktree_result.stderr.strip()}"
                    try:
                        revert_ok = rename_local_branch(temp_branch_name, branch_name)
                    except (FileNotFoundError, OSError) as rename_exc:
                        revert_ok = False
                        error_msg += f" (revert also failed: {rename_exc})"
                    if not revert_ok:
                        error_msg += (
                            f"\nWarning: Failed to revert branch rename. "
                            f"Branch is still named '{temp_branch_name}'. "
                            f"Manually rename it back with: git branch -m {temp_branch_name} {branch_name}"
                        )
                    return WorktreeSetupResult(
                        success=False,
                        worktree_path=worktree_path,
                        branch_name=resolved_branch_name,
                        error_message=error_msg,
                    )

                # Worktree created successfully — rename temp branch to final PR review name.
                # Wrap in try/except so an unexpected git error here doesn't crash
                # create_worktree() after the worktree has already been created.
                print(f"Worktree created successfully at {worktree_path}")
                try:
                    commit_hash_short = get_short_commit_hash(temp_branch_name) or "unknown"
                    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
                    final_review_name = f"{branch_name}-pr-review-{commit_hash_short}-{timestamp}"
                    print(f"Renaming temp branch to final PR review name: '{final_review_name}'...")
                    if not rename_local_branch(temp_branch_name, final_review_name):
                        print(
                            f"Warning: Could not rename temp branch '{temp_branch_name}' to "
                            f"'{final_review_name}'. Temp branch retained."
                        )
                except (FileNotFoundError, OSError) as e:
                    # Non-fatal: the worktree is functional; only the cleanup rename failed.
                    print(
                        f"Warning: Failed to finalize temp branch name: {e}. "
                        f"Branch is still named '{temp_branch_name}'.",
                        file=sys.stderr,
                    )

                _propagate_agdt_cache(worktree_path, worktree_key=issue_key)

                return WorktreeSetupResult(
                    success=True,
                    worktree_path=worktree_path,
                    branch_name=resolved_branch_name,
                )
            else:
                # NOT_ON_BRANCH, or BRANCH_NOT_ON_ORIGIN with no local branch — fail immediately
                return WorktreeSetupResult(
                    success=False,
                    worktree_path=worktree_path,
                    branch_name=resolved_branch_name,
                    error_message=f"Cannot safely create worktree:\n{safety_result.message}",
                )

        print(f"Safety check passed: {safety_result.message}")

        # SAFE status but currently on the target branch in the main repo:
        # switch to main so the git worktree add below doesn't fail with
        # "already checked out".  This is safe here because SAFE guarantees
        # there are no dirty local changes.
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

    # Create the worktree
    try:
        print(f"Creating worktree at {worktree_path}...")

        if use_existing_branch and branch_name:
            # For PR review: checkout existing branch from origin
            result = subprocess.run(
                ["git", "worktree", "add", worktree_path, branch_name],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            if result.returncode != 0:
                # If the branch is already checked out elsewhere, it may be due to a
                # stale worktree association.  Run `git worktree prune` first to remove
                # stale entries, then delete the local ref and retry.
                if "already checked out" in result.stderr.lower():
                    print(
                        f"Branch '{branch_name}' is already checked out. "
                        "Pruning stale worktree entries and deleting local ref before retrying..."
                    )
                    # Best-effort prune — non-fatal if it fails
                    subprocess.run(
                        ["git", "worktree", "prune"],
                        capture_output=True,
                        encoding="utf-8",
                        errors="replace",
                        check=False,
                    )
                    # Use force=True because git branch -d fails for branches not yet
                    # merged into HEAD.  The safety check already confirmed the local ref
                    # matches origin, so force-deleting is safe here.
                    if not delete_local_branch(branch_name, force=True):
                        return WorktreeSetupResult(
                            success=False,
                            worktree_path=worktree_path,
                            branch_name=resolved_branch_name,
                            error_message=(
                                f"Branch '{branch_name}' is already checked out in another worktree "
                                f"and the local ref could not be deleted. "
                                f"Please remove the existing worktree or detach the branch manually."
                            ),
                        )
                # Try tracking the remote branch (covers both the delete+retry case and
                # the case where no local branch exists at all)
                result = subprocess.run(
                    [
                        "git",
                        "worktree",
                        "add",
                        worktree_path,
                        "--track",
                        "-b",
                        branch_name,
                        f"origin/{branch_name}",
                    ],
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
        else:
            # Standard flow: create new branch
            result = subprocess.run(
                ["git", "worktree", "add", worktree_path, "-b", resolved_branch_name],
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            if result.returncode != 0:
                # Check if branch already exists - try without -b
                if "already exists" in result.stderr:
                    print(f"Branch {resolved_branch_name} already exists, using existing branch...")
                    result = subprocess.run(
                        ["git", "worktree", "add", worktree_path, resolved_branch_name],
                        capture_output=True,
                        encoding="utf-8",
                        errors="replace",
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

        _propagate_agdt_cache(worktree_path, worktree_key=issue_key)

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
    # Guard: skip launching external VS Code windows during tests to keep them
    # hermetic.  On Windows, mock paths like /repos/PROJECT-1234 resolve to
    # C:\repos\PROJECT-1234 which may be a real worktree.
    if _in_test_environment():
        print("Detected test environment (PYTEST_CURRENT_TEST) - skipping VS Code window opening")
        return False

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
            encoding="utf-8",
            errors="replace",
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


def _detect_python_scripts_dir() -> str | None:
    """
    Detect the directory containing ``agdt-*`` CLI entry points.

    Tries candidates in priority order and returns the first directory that
    contains an ``agdt-advance-workflow`` executable.  Returns ``None`` if no
    candidate directory contains the entry point.

    Candidate priority:
    1. ``shutil.which("agdt-advance-workflow")`` — if already on PATH, derive
       the directory from the result.
    2. ``~/.agdt/bin`` — the managed install location.
    3. ``sysconfig.get_path("scripts")`` — the Scripts directory of the active
       Python installation (may be a venv).
    4. Directory of ``sys.executable`` and, on Windows, its ``Scripts``
       subdirectory — covers standard CPython layout where the Scripts dir sits
       next to ``python.exe``.

    Returns:
        Absolute path to the directory containing ``agdt-advance-workflow``,
        or ``None`` if not found.
    """
    import sysconfig

    entry_point = "agdt-advance-workflow"
    if sys.platform == "win32":
        entry_point_exe = entry_point + ".exe"
    else:
        entry_point_exe = entry_point

    # Candidate 1: already on PATH — derive directory from which result.
    which_result = shutil.which("agdt-advance-workflow")
    if which_result:
        return os.path.dirname(os.path.realpath(which_result))

    # Candidates 2-4: check directory existence and entry-point presence.
    # entry_point_exe is already platform-appropriate (with or without .exe),
    # so we can use a single path build on all platforms, but also validate
    # executability on POSIX to avoid accepting non-executable files.
    def _contains_entry_point(directory: str) -> bool:
        try:
            candidate_path = os.path.join(directory, entry_point_exe)
            if not os.path.isfile(candidate_path):
                return False
            # On Windows, existence of the .exe file is typically sufficient.
            if os.name == "nt":
                return True
            # On POSIX, require execute permission as well.
            return os.access(candidate_path, os.X_OK)
        except OSError:
            return False

    candidates: list[str] = []

    # Candidate 2: ~/.agdt/bin
    candidates.append(os.path.join(os.path.expanduser("~"), ".agdt", "bin"))

    # Candidate 3: sysconfig Scripts directory
    try:
        scripts_dir = sysconfig.get_path("scripts")
        if scripts_dir:
            candidates.append(scripts_dir)
    except Exception:
        pass

    # Candidate 4: directory containing sys.executable, and on Windows also
    # the ``Scripts`` subdirectory next to it (standard CPython layout:
    # <python_root>\python.exe  +  <python_root>\Scripts\agdt-*.exe).
    if sys.executable:
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(exe_dir)
        if sys.platform == "win32":
            candidates.append(os.path.join(exe_dir, "Scripts"))

    for candidate in candidates:
        try:
            if os.path.isdir(candidate) and _contains_entry_point(candidate):
                return candidate
        except OSError:
            continue

    return None


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
                loaded = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            # Don't overwrite a file we can't parse — it may be JSONC (with
            # comments or trailing commas) which is valid in VS Code but not
            # in stdlib json.  Silently wiping it would destroy user settings.
            print(f"Warning: could not read {settings_path}: {exc}", file=sys.stderr)
            return
        if not isinstance(loaded, dict):
            # A JSON array, string, or other non-object root would cause
            # settings.setdefault(...) to raise AttributeError.
            print(
                f"Warning: {settings_path} does not contain a JSON object at the root; "
                "skipping Git PATH settings injection",
                file=sys.stderr,
            )
            return
        settings = loaded

    # Ensure terminal.integrated.env.windows is a dict before modifying it.
    existing_env_windows = settings.get("terminal.integrated.env.windows")
    if existing_env_windows is None:
        env_windows: dict = {}
        settings["terminal.integrated.env.windows"] = env_windows
    elif isinstance(existing_env_windows, dict):
        env_windows = existing_env_windows
    else:
        print(
            "Warning: terminal.integrated.env.windows is not a JSON object; skipping Git PATH settings injection",
            file=sys.stderr,
        )
        return

    existing_path = env_windows.get("PATH", "${env:PATH}")
    if not isinstance(existing_path, str):
        print(
            "Warning: terminal.integrated.env.windows.PATH is not a string; "
            "falling back to ${env:PATH} for Git PATH settings injection",
            file=sys.stderr,
        )
        existing_path = "${env:PATH}"
    # Split PATH into segments and compare case-insensitively to avoid both
    # false positives from substring matches and missed entries on the
    # case-insensitive Windows filesystem.
    path_segments = {seg.strip().casefold() for seg in existing_path.split(";") if seg.strip()}
    missing_dirs = [d for d in (git_cmd_dir, git_usr_bin_dir) if d.casefold() not in path_segments]
    if missing_dirs:
        env_windows["PATH"] = existing_path + ";" + ";".join(missing_dirs)

    # Avoid unnecessary rewriting of settings.json when no changes are needed
    # and the file already exists, to prevent file churn and noisy diffs.
    if not missing_dirs and os.path.exists(settings_path):
        print(f"Git PATH settings already configured in {settings_path}")
        return

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


def inject_python_path_settings(worktree_path: str) -> None:
    """
    Inject ``.vscode/settings.json`` with the Python Scripts directory that contains ``agdt-*`` entry points.

    When VS Code opens a worktree window, the Python extension may not have
    activated yet (or the user dismisses the "relaunch terminal" prompt),
    leaving the ``agdt-*`` CLI entry points invisible to the Copilot agent.
    This function creates or merges into ``.vscode/settings.json`` a
    ``terminal.integrated.env.*`` entry for the **current runtime platform**
    that prepends the detected Scripts directory to PATH.

    Only the key matching the current runtime platform is injected:

    - ``terminal.integrated.env.windows`` on Windows (``sys.platform == "win32"``)
    - ``terminal.integrated.env.osx`` on macOS (``sys.platform == "darwin"``)
    - ``terminal.integrated.env.linux`` on all other platforms

    This prevents a Windows-style path (e.g. ``C:\\Python...``) from being
    written into the Linux/macOS keys where the drive-letter colon would be
    treated as a PATH separator, corrupting the PATH value in Remote/WSL
    terminals.  Each platform that runs worktree setup contributes its own key.

    The ``is_vscode_available()`` check is intentionally **not** applied here.
    The ``code`` CLI not being on PATH does not prevent VS Code from being
    installed and opening the worktree — VS Code can run integrated terminals
    without the ``code`` command-line utility.  Writing ``.vscode/settings.json``
    is always safe and is picked up the next time VS Code opens the folder.

    A no-op (with a warning to stderr) when:
    - :func:`_detect_python_scripts_dir` cannot find the Scripts directory, or
    - an existing ``settings.json`` cannot be parsed (e.g. JSONC with comments
      or trailing commas) — the file is left untouched so that valid JSONC
      settings are never silently discarded, or
    - ``settings.json`` contains valid JSON but not a root object, or
    - the existing OS-specific env block exists but is not a JSON object.

    When the existing ``PATH`` value is not a string, a warning is emitted and
    the Scripts dir is still injected using ``${env:PATH}`` as the base.

    Args:
        worktree_path: Path to the worktree directory.
    """
    scripts_dir = _detect_python_scripts_dir()
    if scripts_dir is None:
        print(
            "Warning: could not detect Python Scripts directory containing agdt-* entry points; "
            "skipping Python PATH settings injection",
            file=sys.stderr,
        )
        return

    vscode_dir = os.path.join(worktree_path, ".vscode")
    settings_path = os.path.join(vscode_dir, "settings.json")

    settings: dict = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            # Don't overwrite a file we can't parse — it may be JSONC (with
            # comments or trailing commas) which is valid in VS Code but not
            # in stdlib json.  Silently wiping it would destroy user settings.
            print(f"Warning: could not read {settings_path}: {exc}", file=sys.stderr)
            return
        if not isinstance(loaded, dict):
            # A JSON array, string, or other non-object root would cause
            # settings.setdefault / env_block.get to raise AttributeError.
            print(
                f"Warning: {settings_path} does not contain a JSON object at the root; "
                "skipping Python PATH settings injection",
                file=sys.stderr,
            )
            return
        settings = loaded

    # Only inject the terminal env key that matches the current runtime
    # platform.  Writing a Windows path into terminal.integrated.env.linux
    # (or vice versa) would corrupt PATH on the other platform.
    if sys.platform == "win32":
        os_key = "terminal.integrated.env.windows"
        sep = ";"
        case_insensitive = True
    elif sys.platform == "darwin":
        os_key = "terminal.integrated.env.osx"
        sep = ":"
        case_insensitive = False
    else:
        os_key = "terminal.integrated.env.linux"
        sep = ":"
        case_insensitive = False

    # Retrieve or create the env block for this platform, guarding against
    # non-dict values stored under the key (e.g. a JSON string or array).
    existing_env_block = settings.get(os_key)
    if existing_env_block is None:
        env_block: dict = {}
        settings[os_key] = env_block
    elif not isinstance(existing_env_block, dict):
        print(
            f"Warning: {os_key} in {settings_path} is not a JSON object; skipping Python PATH settings injection",
            file=sys.stderr,
        )
        return
    else:
        env_block = existing_env_block

    existing_path_raw = env_block.get("PATH", "${env:PATH}")
    if not isinstance(existing_path_raw, str):
        # PATH stored as a non-string (e.g. list or number) — fall back to the
        # VS Code env-expansion placeholder and warn, but still inject so the
        # agdt-* entry points are on PATH rather than abandoning the operation.
        print(
            f"Warning: PATH value in {os_key} of {settings_path} is not a string "
            f"(got {type(existing_path_raw).__name__!r}); "
            "falling back to ${env:PATH} as the base PATH",
            file=sys.stderr,
        )
        existing_path: str = "${env:PATH}"
    else:
        existing_path = existing_path_raw
    existing_segments = [seg.strip() for seg in existing_path.split(sep) if seg.strip()]

    def _normalize_segment(segment: str) -> str:
        # Normalize a PATH segment for comparison/deduplication:
        # 1. Strip surrounding whitespace.
        # 2. Strip a single pair of surrounding quotes (common on Windows when
        #    PATH entries contain spaces), if present.
        # 3. Apply os.path.normpath.
        cleaned = segment.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
            cleaned = cleaned[1:-1]
        normalized = os.path.normpath(cleaned)
        if case_insensitive:
            return normalized.casefold()
        return normalized

    normalized_existing = {_normalize_segment(s) for s in existing_segments}
    normalized_scripts_dir = _normalize_segment(scripts_dir)
    already_present = normalized_scripts_dir in normalized_existing

    modified = False

    if not already_present:
        env_block["PATH"] = scripts_dir + sep + existing_path
        modified = True

    if not modified and os.path.exists(settings_path):
        print(f"Python PATH settings already configured in {settings_path}")
        return

    try:
        os.makedirs(vscode_dir, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
            fh.write("\n")
        print(f"Injected Python PATH settings into {settings_path}")
    except OSError as exc:
        print(f"Warning: could not write {settings_path}: {exc}", file=sys.stderr)


def inject_task_permission_settings(worktree_path: str) -> None:
    """Inject ``task.allowAutomaticTasks`` into ``.vscode/settings.json``.

    Sets ``"task.allowAutomaticTasks": "on"`` so that tasks with
    ``"runOn": "folderOpen"`` execute immediately when VS Code opens
    the workspace, without prompting the user.

    The ``is_vscode_available()`` check is intentionally **not** applied
    here — writing ``.vscode/settings.json`` is always safe, following
    the same reasoning as :func:`inject_python_path_settings`.

    Behavior by existing value:

    - Missing, ``"auto"``, or any other unexpected value: set to ``"on"``
      (eliminates the permission dialog).
    - ``"on"``: no-op (already configured).
    - ``"off"``: no-op with warning (respects explicit user choice).

    A no-op (with a warning to stderr) when:

    - An existing ``settings.json`` cannot be parsed (e.g. JSONC), or
    - ``settings.json`` contains valid JSON but not a root object.

    Args:
        worktree_path: Path to the worktree directory.
    """
    _SETTING_KEY = "task.allowAutomaticTasks"

    vscode_dir = os.path.join(worktree_path, ".vscode")
    settings_path = os.path.join(vscode_dir, "settings.json")

    settings: dict = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(
                f"Warning: could not read {settings_path}: {exc}",
                file=sys.stderr,
            )
            return
        if not isinstance(loaded, dict):
            print(
                f"Warning: {settings_path} does not contain a JSON object at the root; "
                "skipping task permission settings injection",
                file=sys.stderr,
            )
            return
        settings = loaded

    existing_value = settings.get(_SETTING_KEY)

    if existing_value == "on":
        print(f"Task permission settings already configured in {settings_path}")
        return

    if existing_value == "off":
        print(
            f'Warning: {_SETTING_KEY} is set to "off" in {settings_path}; '
            "automatic tasks are disabled by user choice — skipping injection",
            file=sys.stderr,
        )
        return

    # Value is missing, "auto", or any other unexpected value — set to "on".
    settings[_SETTING_KEY] = "on"

    try:
        os.makedirs(vscode_dir, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
            fh.write("\n")
        print(f"Injected task permission settings into {settings_path}")
    except OSError as exc:
        print(f"Warning: could not write {settings_path}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Label used to identify the injected auto-start task so it can be removed
# during cleanup without affecting other user-defined tasks.
# ---------------------------------------------------------------------------
_AUTO_START_TASK_LABEL = "agdt-copilot-auto-start"


def _remove_stale_auto_start_task(
    tasks_path: str,
    vscode_dir: str,
    task_label: str,
) -> None:
    """Best-effort remove a stale auto-start task from ``tasks.json``.

    Thin wrapper around :func:`~agentic_devtools.cli.vscode_tasks.remove_auto_start_task`
    that preserves the original signature used by :func:`inject_auto_start_task`.

    Called when the current run ID is already in the triggered set, indicating
    a previous run succeeded but its cleanup may have failed.  If the task is
    found and removed:

    * When other tasks remain the file is rewritten.
    * When no tasks remain **and** the stale task's ``"args"`` list contained
      ``"--created-new"`` (meaning the file was created fresh by the injection)
      **and** the file has no other top-level keys besides ``version`` and
      ``tasks``, the file is **deleted** and ``.vscode/`` is removed if empty.
    * In all other cases (old-format tasks without ``"args"``, missing flag, or
      extra top-level keys) the file is rewritten, never deleted — this prevents
      inadvertent deletion of a pre-existing user ``tasks.json``.

    All errors are silently caught so this never prevents the caller from
    proceeding.
    """
    # Infer delete_if_empty by inspecting the stale task's "args" list.
    # Default to False (conservative) when the task cannot be read, has no
    # "args", or the "--created-new" flag is absent — this prevents inadvertent
    # deletion of a pre-existing user tasks.json.
    delete_if_empty = False
    try:
        if os.path.isfile(tasks_path):
            with open(tasks_path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                tasks_list = data.get("tasks")
                if isinstance(tasks_list, list):
                    for task in tasks_list:
                        if isinstance(task, dict) and task.get("label") == task_label:
                            args = task.get("args", [])
                            delete_if_empty = isinstance(args, list) and "--created-new" in args
                            break
    except Exception:
        pass
    remove_auto_start_task(tasks_path, vscode_dir, task_label, delete_if_empty=delete_if_empty)


class WorktreeStateContext:
    """Context manager for cross-worktree state resolution.

    Saves the current CWD and state-related env vars, clears them, and
    changes to *worktree_path* so that ``get_state_dir()`` /
    ``get_state_file_path()`` resolve from the target worktree's
    ``.agdt/runtime-bootstrap.json``. On exit it makes a best-effort
    attempt to restore the original CWD and env vars.

    Usage::

        with WorktreeStateContext(worktree_path):
            state_dir = get_state_dir()   # resolves in worktree context
    """

    _ENV_VARS = ("AGENTIC_DEVTOOLS_STATE_DIR", "AGDT_AI_HELPERS_STATE_DIR")

    def __init__(self, worktree_path: str) -> None:
        self.worktree_path = worktree_path
        self._previous_cwd: str = ""
        self._previous_env: dict[str, str | None] = {}

    def __enter__(self) -> WorktreeStateContext:
        self._previous_cwd = os.getcwd()
        for var in self._ENV_VARS:
            self._previous_env[var] = os.environ.pop(var, None)
        try:
            os.chdir(self.worktree_path)
        except Exception:
            # Restore env vars before re-raising since __exit__ won't run.
            self._restore_env_vars()
            raise
        return self

    def __exit__(self, *exc_info: object) -> None:
        try:
            os.chdir(self._previous_cwd)
        except OSError:
            pass

        self._restore_env_vars()

    def _restore_env_vars(self) -> None:
        for var in self._ENV_VARS:
            try:
                prev = self._previous_env.get(var)
                if prev is not None:
                    os.environ[var] = prev
                else:
                    os.environ.pop(var, None)
            except Exception:
                pass


#: Convenience alias so call sites read as ``with worktree_state_context(...):``
worktree_state_context = WorktreeStateContext


def _resolve_state_context_in_worktree(
    worktree_path: str,
    *,
    include_run_id: bool = False,
) -> tuple[Path | None, str]:
    """Resolve workflow state using the target worktree context."""
    try:
        with worktree_state_context(worktree_path):
            from agentic_devtools.state import get_state_file_path

            state_file_path = get_state_file_path()
            run_id = ""
            if include_run_id:
                from agentic_devtools.state import get_value

                run_id_value = get_value("agdt_run_id")
                run_id = run_id_value.strip() if isinstance(run_id_value, str) else ""
            return state_file_path, run_id
    except Exception:
        return None, ""


def inject_auto_start_task(
    worktree_path: str,
    start_prompt: str,
    run_id: str,
    task_label: str = _AUTO_START_TASK_LABEL,
    model: str | None = None,
) -> bool:
    """Write a ``.vscode/tasks.json`` task that auto-runs when the folder opens.

    The task is configured with ``"runOn": "folderOpen"`` so that VS Code
    executes ``agdt-copilot-auto-start`` in the integrated terminal immediately
    when the workspace window opens.  All run-ID-check, copilot-invocation,
    and cleanup logic is delegated to that CLI command.

    The task uses VS Code's ``"type": "process"`` format, which means VS Code
    passes ``command`` and each element of ``args`` directly to the OS without
    going through a shell.  This eliminates all quoting and escaping concerns
    on both Windows (cmd.exe) and Unix regardless of the characters in the
    worktree path or start prompt.

    When ``tasks.json`` did not exist before injection the ``--created-new``
    flag is passed so cleanup can delete the file instead of rewriting when no
    tasks remain.

    The function merges the new task into an existing ``tasks.json`` if one
    is present, preserving any user-defined tasks.

    This is a **no-op** when ``is_vscode_available()`` returns ``False``.

    Args:
        worktree_path: Absolute path to the worktree directory.
        start_prompt: The prompt text to pass to the Copilot binary via
            ``agdt-copilot-auto-start --start-prompt``.
        run_id: Unique run ID for this workflow invocation.  Passed
            through to ``agdt-copilot-auto-start --run-id``.
        task_label: Label for the injected task (default:
            ``"agdt-copilot-auto-start"``).  Used to identify the task
            during cleanup.
        model: Optional Copilot model ID (e.g. ``"gpt-4o"``).
            When not ``None``, ``--model <model>`` is appended to the
            ``agdt-copilot-auto-start`` args so the auto-start session
            uses the same model as the workflow that triggered it.

    Returns:
        ``True`` if the task was written successfully, ``False`` otherwise
        (e.g. VS Code not available, filesystem errors).
    """
    if not is_vscode_available():
        return False

    # Validate that the start_prompt is a non-empty string.
    if not start_prompt or not isinstance(start_prompt, str):
        return False

    # Validate that the worktree path exists and is a directory. A bad or
    # typo path would otherwise cause us to create stray folders when
    # calling os.makedirs(vscode_dir, ...).
    if not worktree_path or not os.path.isdir(worktree_path):
        return False

    vscode_dir = os.path.join(worktree_path, ".vscode")
    tasks_path = os.path.join(vscode_dir, "tasks.json")

    # Skip injection when the run ID has already been triggered — the command
    # was already executed successfully in a previous window open.  Without
    # this guard the task would be written but then exit immediately in
    # the run-ID short-circuit, leaving an orphaned entry in tasks.json.
    normalized_run_id: str | None
    if isinstance(run_id, str):
        normalized_run_id = run_id.strip()
        if not normalized_run_id:
            normalized_run_id = None
    else:
        normalized_run_id = None

    if normalized_run_id:
        from agentic_devtools.cli.copilot.auto_start import _is_run_triggered

        state_file_path, _ = _resolve_state_context_in_worktree(worktree_path)
        if state_file_path and _is_run_triggered(state_file_path, normalized_run_id):
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

    # --- Build the simple CLI invocation -------------------------------------
    # Delegate all run-ID-check, copilot-invocation, and cleanup logic to
    # agdt-copilot-auto-start.  Using a "process"-type task with a separate
    # "command" + "args" array means VS Code passes each argument directly to
    # the process without going through a shell, so no quoting or escaping is
    # needed regardless of the platform or the characters in the path/prompt.
    if not isinstance(run_id, str) or not run_id.strip():
        # Without a non-empty, non-whitespace string run_id we would generate a
        # broken auto-start task that fails on every folderOpen.  Instead of
        # raising (the function is documented as returning bool), log a warning
        # and skip injection.
        print(
            "Warning: inject_auto_start_task called with invalid run_id; skipping auto-start task injection.",
            file=sys.stderr,
        )
        return False

    command_args = [
        "--worktree-path",
        worktree_path,
        "--start-prompt",
        start_prompt,
        "--task-label",
        task_label,
        "--run-id",
        run_id.strip(),
    ]
    if not file_existed:
        command_args.append("--created-new")
    # Normalize model: treat empty/whitespace-only strings as "not provided"
    # so that the auto-start command falls back to its state → default chain
    # rather than receiving a blank --model value.
    normalized_model: str | None = None
    if isinstance(model, str):
        stripped = model.strip()
        if stripped:
            normalized_model = stripped
    if normalized_model is not None:
        command_args.extend(["--model", normalized_model])

    # --- Build the task definition -------------------------------------------
    task_def = {
        "label": task_label,
        "type": "process",
        "command": "agdt-copilot-auto-start",
        "args": command_args,
        "runOptions": {"runOn": "folderOpen"},
        "presentation": {
            "reveal": "always",
            "focus": True,
        },
        "problemMatcher": [],
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
    branch_name: str | None = None,
    use_existing_branch: bool = False,
    open_vscode: bool = True,
) -> WorktreeSetupResult:
    """
    Complete worktree setup: create worktree and open VS Code.

    This is the main entry point for setting up a new development environment
    for an issue. It:
    1. Creates a git worktree for the issue
    2. Injects ``.vscode/settings.json`` with Git for Windows PATH entries (Windows only)
    3. Injects ``.vscode/settings.json`` with Python Scripts directory PATH entries (all platforms)
    4. Injects ``task.allowAutomaticTasks: "on"`` into ``.vscode/settings.json`` (all platforms)
    5. Runs ``.agdt/agentic-devtools-worktree-setup.py`` if present
    6. Opens VS Code with the workspace file

    Args:
        issue_key: The issue key (e.g., "PROJECT-1234")
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

    # Step 3: Inject VS Code settings for Python/agdt-* Scripts PATH (all platforms)
    inject_python_path_settings(result.worktree_path)

    # Step 4: Inject task.allowAutomaticTasks permission for runOn:folderOpen tasks
    inject_task_permission_settings(result.worktree_path)

    # Step 5: Run project-specific worktree setup script if present
    run_worktree_setup_script(result.worktree_path)

    # Step 6: Open VS Code
    if open_vscode:
        result.vscode_opened = open_vscode_workspace(result.worktree_path)

    return result


def check_worktree_exists(issue_key: str) -> str | None:
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
    user_request: str | None = None,
    additional_params: dict | None = None,
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
    user_request: str | None = None,
    additional_params: dict | None = None,
) -> str:
    """
    Generate a detailed prompt for AI agents to continue working on an issue.

    This is used when a new VS Code window is opened in a worktree to provide
    the AI agent with clear instructions on how to proceed.

    Args:
        issue_key: The Jira issue key (e.g., "PROJECT-1234") or PR identifier (e.g., "PR24031")
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
        action_description = "analyze the Jira issue and create subtasks via agdt-initiate-create-jira-subtask-workflow"
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
    # target worktree's identity-scoped state directory whenever a valid
    # ``identity`` (read from ``.agdt/identity.json`` when present, otherwise
    # from ``runtime-bootstrap.json``) and ``worktree_key`` (from
    # ``runtime-bootstrap.json``) can be resolved. Falls back to ``_unscoped``
    # when either file is missing, unreadable, or malformed, when either key
    # is absent or empty, or when either segment fails ``is_safe_dir_segment()``
    # validation. This propagates into any nested background tasks spawned by
    # the auto-execute command so that prompt files and state are written to
    # the correct worktree location instead of falling back to a
    # Python-install-relative temp directory.
    env = os.environ.copy()

    # Read identity from the identity cache file (new) with fallback to runtime-bootstrap.json (legacy).
    # worktree_key always comes from runtime-bootstrap.json.
    identity_cache_path = Path(worktree_path) / ".agdt" / IDENTITY_CACHE_FILENAME
    identity = ""
    worktree_key = ""
    try:
        if identity_cache_path.is_file():
            data = json.loads(identity_cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw_id = data.get("identity", "")
                identity = raw_id.strip() if isinstance(raw_id, str) else ""
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        pass

    bootstrap_path = Path(worktree_path) / ".agdt" / "runtime-bootstrap.json"
    try:
        if bootstrap_path.is_file():
            data = json.loads(bootstrap_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                raw_wk = data.get("worktree_key", "")
                worktree_key = raw_wk.strip() if isinstance(raw_wk, str) else ""
                # Legacy fallback: read identity from bootstrap when identity.json absent
                if not identity:
                    raw_id = data.get("identity", "")
                    identity = raw_id.strip() if isinstance(raw_id, str) else ""
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
            encoding="utf-8",
            errors="replace",
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
    model: str | None = None,
) -> bool:
    """Wait for the workflow setup to complete, then start a ``gh copilot`` session.

    This is the generic helper that all workflow-specific wrappers delegate
    to.  It waits for a prompt file to appear on disk, detects VS Code /
    TTY availability, handles the auto-start task run-ID check, and
    finally calls :func:`start_copilot_session`.

    **Auto-start task handling**: The VS Code auto-start task is injected
    *before* VS Code opens (by :func:`_maybe_inject_auto_start_before_vscode`
    in the background worktree setup flow).  When this function detects the
    task was already injected and there is no TTY attached (background task
    scenario), it waits for the run ID to appear in
    ``copilot.auto_start_triggered_runs`` to confirm VS Code handled the
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
    # briefly for the run ID to appear in ``copilot.auto_start_triggered_runs``
    # confirming the VS Code task actually started.  If the run ID appears,
    # VS Code is handling the session and we can skip.  If it doesn't appear
    # within a reasonable window (e.g. VS Code failed to open or the task
    # didn't fire), we fall through and start the session ourselves as a
    # fallback.
    # NOTE: The check intentionally does NOT require interactive=True.
    # Injection happens regardless of the interactive flag (see
    # _maybe_inject_auto_start_before_vscode), so we must check for the
    # auto-start task even when interactive=False.
    if not has_tty and is_vscode_available():
        tasks_path = os.path.join(worktree_path, ".vscode", "tasks.json")
        if os.path.exists(tasks_path):
            try:
                with open(tasks_path, encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    tasks_list = data.get("tasks")
                    if not isinstance(tasks_list, list):
                        tasks_list = []
                    if any(isinstance(t, dict) and t.get("label") == _AUTO_START_TASK_LABEL for t in tasks_list):
                        from agentic_devtools.cli.copilot.auto_start import _is_run_triggered

                        state_file_path, current_run_id = _resolve_state_context_in_worktree(
                            worktree_path,
                            include_run_id=True,
                        )

                        if state_file_path:
                            # If we have a state file but no current run ID, there is
                            # nothing meaningful to wait for. This can happen when a
                            # stale tasks.json is present but no VS Code task has
                            # populated the run ID yet. In that case we must fall
                            # through immediately so the user still gets a Copilot
                            # session without an unconditional delay.
                            if not current_run_id:
                                print(
                                    "\n--- VS Code auto-start task present but no run ID "
                                    "is available in state. Falling back to background "
                                    "Copilot session. ---"
                                )
                            # Check whether the run ID is already triggered *before*
                            # we start waiting.  A pre-existing triggered run ID
                            # (e.g. from a previous run) would cause the VS Code
                            # task to exit immediately without starting a session.
                            # In that case we must fall through to the background
                            # session so the user still gets a Copilot session.
                            elif _is_run_triggered(state_file_path, current_run_id):
                                print(
                                    "\n--- Run ID already triggered. "
                                    "VS Code task will skip; falling back to "
                                    "background Copilot session. ---"
                                )
                            else:
                                print(
                                    "\n--- VS Code auto-start task present. "
                                    "Waiting for VS Code to start the Copilot session... ---"
                                )
                                # Wait up to 15 seconds for the run ID to appear in state,
                                # which means the VS Code task actually executed.
                                import time

                                _TRIGGERED_WAIT_SECONDS = 15
                                _TRIGGERED_POLL_INTERVAL = 1.0
                                waited = 0.0
                                while waited < _TRIGGERED_WAIT_SECONDS:
                                    if _is_run_triggered(state_file_path, current_run_id):
                                        print(
                                            "--- VS Code auto-start task confirmed running. "
                                            "Copilot session is in the integrated terminal. ---"
                                        )
                                        return True
                                    time.sleep(_TRIGGERED_POLL_INTERVAL)
                                    waited += _TRIGGERED_POLL_INTERVAL
                                print(
                                    "--- VS Code auto-start task did not fire within "
                                    f"{_TRIGGERED_WAIT_SECONDS}s. "
                                    "Trying terminal sendSequence fallback... ---"
                                )
                                if _try_terminal_send_fallback(worktree_path, expected_run_id=current_run_id):
                                    return True
                                print("--- Falling back to background Copilot session. ---")
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
    # start_copilot_session() resolves paths via get_state_dir(), so we enter
    # worktree_state_context(worktree_path), which changes into the target worktree
    # and clears both AGENTIC_DEVTOOLS_STATE_DIR and the legacy
    # AGDT_AI_HELPERS_STATE_DIR override variables for cross-worktree resolution.
    # We then set AGENTIC_DEVTOOLS_STATE_DIR to the resolved target state dir so
    # downstream writes stay pinned to the target worktree for this session.
    with worktree_state_context(worktree_path):
        from ...state import get_state_dir

        state_dir = get_state_dir()
        os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = str(state_dir)
        start_copilot_session(
            prompt=start_prompt,
            working_directory=worktree_path,
            interactive=effective_interactive,
            model=model,
        )
        return True


def _start_copilot_session_for_pr_review(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the pull-request-review workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies PR-review-specific parameters (prompt file path and start
    prompt text).

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
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
    with worktree_state_context(worktree_path):
        state_dir = get_state_dir()
        return os.path.relpath(str(state_dir / prompt_filename), worktree_path)


def _start_copilot_session_for_apply_pr_suggestions(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the apply-pull-request-review-suggestions workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies apply-pr-suggestions-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
    )


def _start_copilot_session_for_work_on_jira_issue(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the work-on-jira-issue workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies work-on-jira-issue-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
    )


def _start_copilot_session_for_create_jira_issue(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the create-jira-issue workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies create-jira-issue-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
    )


def _start_copilot_session_for_create_jira_epic(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the create-jira-epic workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies create-jira-epic-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
    )


def _start_copilot_session_for_create_jira_subtask(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the create-jira-subtask workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies create-jira-subtask-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
    )


def _start_copilot_session_for_update_jira_issue(
    worktree_path: str,
    interactive: bool = False,
    model: str | None = None,
) -> bool:
    """Start a Copilot session for the update-jira-issue workflow.

    Thin wrapper around :func:`_start_copilot_session_for_workflow` that
    supplies update-jira-issue-specific parameters.

    Args:
        worktree_path: Absolute path to the worktree root.
        interactive: Whether to start the Copilot session interactively.
        model: Optional Copilot model ID to use.

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
        model=model,
    )


_PENDING_AUTO_START_FILENAME = "pending-auto-start.json"


def _write_pending_auto_start_marker(
    worktree_path: str,
    run_id: str,
    start_prompt: str,
    model: str | None = None,
) -> None:
    """Write a JSON marker file for the terminal-send fallback mechanism.

    The marker is written to ``<worktree_path>/.vscode/pending-auto-start.json``
    and contains the parameters needed to reconstruct the
    ``agdt-copilot-auto-start`` command line if the primary ``runOn: folderOpen``
    task does not fire.

    This is a best-effort operation: errors are printed to stderr but never
    raised to the caller.
    """
    from datetime import datetime, timezone

    vscode_dir = os.path.join(worktree_path, ".vscode")
    marker_path = os.path.join(vscode_dir, _PENDING_AUTO_START_FILENAME)
    marker = {
        "run_id": run_id,
        "start_prompt": start_prompt,
        "model": model,
        "worktree_path": worktree_path,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "task_label": _AUTO_START_TASK_LABEL,
    }
    try:
        os.makedirs(vscode_dir, exist_ok=True)
        with open(marker_path, "w", encoding="utf-8") as fh:
            json.dump(marker, fh, indent=2, ensure_ascii=False)
    except OSError as exc:
        print(
            f"Warning: failed to write pending auto-start marker at {marker_path}: {exc}",
            file=sys.stderr,
        )


def _cleanup_pending_auto_start_marker(worktree_path: str) -> None:
    """Delete the pending auto-start marker file if it exists.

    Best-effort: errors are printed to stderr but never raised.
    """
    marker_path = os.path.join(worktree_path, ".vscode", _PENDING_AUTO_START_FILENAME)
    try:
        if os.path.exists(marker_path):
            os.remove(marker_path)
    except OSError as exc:
        print(
            f"Warning: failed to remove pending auto-start marker at {marker_path}: {exc}",
            file=sys.stderr,
        )


def _try_terminal_send_fallback(worktree_path: str, expected_run_id: str | None = None) -> bool:
    """Attempt to start the Copilot session via VS Code terminal sendSequence.

    Reads the ``pending-auto-start.json`` marker file, constructs the
    ``agdt-copilot-auto-start`` command, and sends it to the VS Code
    integrated terminal using ``code --command workbench.action.terminal.sendSequence``.

    When *expected_run_id* is provided, the marker's ``run_id`` must match it
    exactly.  This prevents stale markers (from a prior run) from triggering
    a false-positive confirmation and causing the caller to skip starting a
    new background Copilot session.

    Returns ``True`` when the fallback session was confirmed (run ID appeared
    in ``copilot.auto_start_triggered_runs`` within 15 seconds), ``False``
    otherwise.

    This function is a **no-op** (returns ``False``) when running in a test
    environment, mirroring the guard in ``_maybe_inject_auto_start_before_vscode()``.
    """
    import time

    if _in_test_environment():
        return False

    marker_path = os.path.join(worktree_path, ".vscode", _PENDING_AUTO_START_FILENAME)
    if not os.path.isfile(marker_path):
        return False

    try:
        with open(marker_path, encoding="utf-8") as fh:
            marker = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return False

    if not isinstance(marker, dict):
        return False

    run_id = marker.get("run_id")
    start_prompt = marker.get("start_prompt")
    if not isinstance(run_id, str) or not run_id or not isinstance(start_prompt, str) or not start_prompt:
        return False

    if expected_run_id and run_id != expected_run_id:
        print(
            f"--- Terminal sendSequence fallback: marker run_id ({run_id}) "
            f"does not match expected run_id ({expected_run_id}). Skipping stale marker. ---"
        )
        return False

    # Build the agdt-copilot-auto-start command line.
    # Validate that all values destined for _shell_quote() are strings;
    # a corrupted marker file could contain non-str values that would
    # cause AttributeError/TypeError in _shell_quote().
    wt_path = marker.get("worktree_path")
    model = marker.get("model")
    if not isinstance(wt_path, str):
        wt_path = worktree_path
    cmd_parts: list[str] = [
        "agdt-copilot-auto-start",
        "--worktree-path",
        wt_path,
        "--start-prompt",
        start_prompt,
        "--run-id",
        run_id,
    ]
    if isinstance(model, str) and model:
        cmd_parts.extend(["--model", model])

    command_string = " ".join(_shell_quote(p) for p in cmd_parts)
    send_sequence_arg = json.dumps({"text": command_string + "\n"})

    print("--- Attempting terminal sendSequence fallback for auto-start... ---")

    try:
        use_shell = platform.system() == "Windows"
        proc = subprocess.run(  # noqa: S603, S607
            ["code", "--command", "workbench.action.terminal.sendSequence", send_sequence_arg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            shell=use_shell,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("--- Terminal sendSequence fallback: 'code --command' failed or timed out. ---")
        return False

    if proc.returncode != 0:
        print(f"--- Terminal sendSequence fallback: 'code --command' exited with code {proc.returncode}. ---")
        return False

    # Wait up to 15 seconds for the run ID to appear in state
    from agentic_devtools.cli.copilot.auto_start import _is_run_triggered

    state_file_path, _ = _resolve_state_context_in_worktree(worktree_path)
    if not state_file_path:
        return False

    _FALLBACK_WAIT_SECONDS = 15
    _FALLBACK_POLL_INTERVAL = 1.0
    waited = 0.0
    while waited < _FALLBACK_WAIT_SECONDS:
        if _is_run_triggered(state_file_path, run_id):
            print("--- Terminal sendSequence fallback confirmed: Copilot session is in the integrated terminal. ---")
            _cleanup_pending_auto_start_marker(worktree_path)
            return True
        time.sleep(_FALLBACK_POLL_INTERVAL)
        waited += _FALLBACK_POLL_INTERVAL

    print(f"--- Terminal sendSequence fallback: run ID not confirmed within {_FALLBACK_WAIT_SECONDS}s. ---")
    return False


def _shell_quote(s: str) -> str:
    """Quote a string for safe embedding in a shell command.

    Uses :func:`shlex.quote` on non-Windows platforms. On Windows, wraps
    the string in double quotes, doubles embedded double quotes, and
    doubles percent signs to avoid ``%VAR%`` expansion by ``cmd.exe``.

    Note: The quoted strings are embedded in a VS Code terminal
    ``sendSequence`` text payload. The data originates from the
    ``pending-auto-start.json`` marker file that we wrote ourselves, so
    injection risk is minimal.
    """
    if platform.system() == "Windows":
        # This Windows branch does not attempt full cmd.exe metacharacter
        # escaping. It only doubles embedded double quotes and percent
        # signs, then wraps the result in double quotes.
        escaped = s.replace('"', '""').replace("%", "%%")
        return '"' + escaped + '"'
    import shlex  # noqa: PLC0415 — lazy import; not needed on Windows

    return shlex.quote(s)


def _maybe_inject_auto_start_before_vscode(
    worktree_path: str,
    start_prompt: str = COPILOT_SESSION_START_PROMPT,
    model: str | None = None,
    run_id: str | None = None,
) -> bool:
    """Inject a VS Code auto-start task before VS Code opens.

    Called right before ``open_vscode_workspace()`` so the task exists when
    the ``folderOpen`` event fires.  Uses *start_prompt* to tell the Copilot
    agent which workflow to execute — callers should pass the correct
    workflow-specific prompt (see :data:`_WORKFLOW_START_PROMPTS`).

    Injection is attempted regardless of the ``interactive`` flag passed to
    the outer worktree-setup flow.  Internal guards (``is_vscode_available()``,
    run-ID state check, etc.) prevent inappropriate injection.

    This is a best-effort helper: if ``build_copilot_args()`` returns
    ``None`` (start prompt exceeds argv limits) or ``inject_auto_start_task()`` fails,
    the caller continues without the auto-start task; the existing
    fallback behaviour in the workflow-specific session launcher will
    handle the session.  Each non-trivial failure path prints a diagnostic
    message to stdout so that log files capture why injection was skipped
    (the ``_in_test_environment()`` guard returns silently).

    Args:
        run_id: Optional pre-generated run ID.  When provided (non-empty
            after stripping whitespace), the function uses it directly
            instead of reading ``agdt_run_id`` from the target worktree's
            state — this eliminates the race condition where the background
            task that writes ``agdt_run_id`` hasn't completed yet.  When
            ``None`` or empty/whitespace, the existing read-from-state
            behaviour is preserved.

    Returns:
        ``True`` if the auto-start task was successfully written to
        ``tasks.json``, ``False`` otherwise.
    """
    # Guard: skip writing tasks.json to real filesystem paths during tests to
    # keep them hermetic.  On Windows, mock paths like /repos/PROJECT-1234 resolve
    # to C:\repos\PROJECT-1234 which may be a real worktree — writing
    # runOn:folderOpen tasks there causes VS Code to open unexpected windows.
    if _in_test_environment():
        return False

    from ..copilot import build_copilot_args

    # Determine the run ID: use the caller-provided value if it's a
    # non-empty string after stripping whitespace; otherwise fall back to
    # reading from the target worktree's state.
    provided_run_id = run_id.strip() if isinstance(run_id, str) else ""
    if provided_run_id:
        # Caller pre-generated a run ID — skip the state read for run_id
        # but still resolve state_file_path for the _is_run_triggered guard.
        state_file_path, _ = _resolve_state_context_in_worktree(worktree_path, include_run_id=False)
        if state_file_path is None:
            print(f"Auto-start injection skipped: could not resolve state context in {worktree_path}.")
            return False
        run_id = provided_run_id
    else:
        # Read the run ID from the TARGET worktree's state context,
        # not the parent process's state.
        state_file_path, run_id = _resolve_state_context_in_worktree(worktree_path, include_run_id=True)

        if state_file_path is None:
            # _resolve_state_context_in_worktree failed (unreadable state).
            print(f"Auto-start injection skipped: could not read agdt_run_id from state in {worktree_path}.")
            return False

        if not run_id:
            # run_id is empty — the agdt_run_id value is missing or was
            # whitespace-only in the target worktree's state.
            print(f"Auto-start injection skipped: missing or empty agdt_run_id in {worktree_path}.")
            return False

    # Write marker BEFORE injection so the terminal sendSequence fallback
    # is available even when inject_auto_start_task() fails.
    _write_pending_auto_start_marker(worktree_path, run_id, start_prompt, model=model)

    copilot_args = build_copilot_args(start_prompt, interactive=True, model=model)
    if copilot_args is not None:
        injected = inject_auto_start_task(worktree_path, start_prompt, run_id=run_id, model=model)
        if injected:
            print("   VS Code auto-start task injected (will run on window open).")
        else:
            print(
                "WARNING: VS Code auto-start task injection failed. "
                "Auto-start is disabled; Copilot session fallback will be used."
            )
        return injected
    print("Auto-start injection skipped: Copilot prompt exceeds argv limits.")
    return False


def setup_worktree_in_background_sync(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: str | None = None,
    use_existing_branch: bool = False,
    workflow_name: str = "work-on-jira-issue",
    user_request: str | None = None,
    additional_params: dict | None = None,
    auto_execute_command: list[str] | None = None,
    auto_execute_timeout: int = 60,
    interactive: bool = False,
    model: str | None = None,
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
            (default: 60).
        interactive: Whether to start the Copilot session interactively after
            setup (default: False). Set to True for interactive mode.
        model: Copilot model identifier to use for the session (e.g.
            ``"claude-3.5-sonnet"``).  Passed through to
            ``_maybe_inject_auto_start_before_vscode()`` so the model is
            resolved from the caller's context rather than from state.
    """
    import uuid

    from ...state import set_value

    # Pre-generate a run ID for auto-start injection.  This eliminates
    # the race condition where the background task spawned by the
    # auto-execute command hasn't written ``agdt_run_id`` to state yet
    # when ``_maybe_inject_auto_start_before_vscode()`` tries to read it.
    pre_run_id = uuid.uuid4().hex[:12]

    print(f"\n{'=' * 80}")
    print("BACKGROUND WORKTREE SETUP")
    print("=" * 80)

    # Check if worktree already exists
    existing_path = check_worktree_exists(issue_key)
    if existing_path:
        print(f"\nWorktree already exists at: {existing_path}")

        wf_prompt = _WORKFLOW_START_PROMPTS.get(workflow_name, _WORKFLOW_AGNOSTIC_FALLBACK_PROMPT)

        # Inject VS Code settings so agdt-* commands are on PATH and
        # runOn:folderOpen tasks execute without a permission prompt.  Do this
        # every time VS Code is opened (not only on first creation) so that
        # worktrees created before this feature, or opened on a different
        # machine, also benefit.
        inject_git_path_settings(existing_path)
        inject_python_path_settings(existing_path)
        inject_task_permission_settings(existing_path)

        # When a data-fetching command is provided, run it first so that all
        # workflow context is ready before VS Code opens.  The auto-start task
        # fires on ``folderOpen``, so completing data-fetching before opening
        # the window ensures the Copilot agent starts with full context.
        if auto_execute_command:
            exit_code = _run_auto_execute_command(auto_execute_command, existing_path, auto_execute_timeout)
            set_value("worktree_setup.auto_execute_exit_code", str(exit_code))

        # Inject VS Code auto-start task *before* opening the window so that
        # the ``runOn: folderOpen`` event fires with the task already present.
        _maybe_inject_auto_start_before_vscode(existing_path, start_prompt=wf_prompt, model=model, run_id=pre_run_id)

        # Open VS Code
        print("Opening VS Code in the existing worktree (using the workspace file if available)...")
        vscode_opened = open_vscode_workspace(existing_path)
        print(f"   VS Code opened: {'Yes' if vscode_opened else 'No'}")

        # Start Copilot session as a secondary fallback.  The primary
        # mechanism is the VS Code ``runOn: folderOpen`` task injected above;
        # this call provides the 15-second wait + terminal sendSequence +
        # background session fallback chain.
        prompt_filename = _WORKFLOW_PROMPT_FILENAMES.get(workflow_name)
        if prompt_filename:
            _start_copilot_session_for_workflow(
                worktree_path=existing_path,
                prompt_file_relative_path=_prompt_file_relative_path(existing_path, prompt_filename),
                start_prompt=wf_prompt,
                workflow_name=workflow_name,
                interactive=interactive,
                model=model,
            )

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
        wf_prompt = _WORKFLOW_START_PROMPTS.get(workflow_name, _WORKFLOW_AGNOSTIC_FALLBACK_PROMPT)

        # When a data-fetching command is provided, run it first so that all
        # workflow context is ready before VS Code opens.  The auto-start task
        # fires on ``folderOpen``, so completing data-fetching before opening
        # the window ensures the Copilot agent starts with full context.
        if auto_execute_command:
            exit_code = _run_auto_execute_command(auto_execute_command, result.worktree_path, auto_execute_timeout)
            set_value("worktree_setup.auto_execute_exit_code", str(exit_code))

        # Inject VS Code auto-start task *before* opening the window so that
        # the ``runOn: folderOpen`` event fires with the task already present.
        _maybe_inject_auto_start_before_vscode(
            result.worktree_path,
            start_prompt=wf_prompt,
            model=model,
            run_id=pre_run_id,
        )

        # Open VS Code after task injection
        result.vscode_opened = open_vscode_workspace(result.worktree_path)

        # Start Copilot session as a secondary fallback.  The primary
        # mechanism is the VS Code ``runOn: folderOpen`` task injected above;
        # this call provides the 15-second wait + terminal sendSequence +
        # background session fallback chain.
        prompt_filename = _WORKFLOW_PROMPT_FILENAMES.get(workflow_name)
        if prompt_filename:
            _start_copilot_session_for_workflow(
                worktree_path=result.worktree_path,
                prompt_file_relative_path=_prompt_file_relative_path(result.worktree_path, prompt_filename),
                start_prompt=wf_prompt,
                workflow_name=workflow_name,
                interactive=interactive,
                model=model,
            )

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
    # Normalize to str | None — get_value() returns Any.
    model_raw = get_value("worktree_setup.model")
    model = (model_raw.strip() or None) if isinstance(model_raw, str) else None

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

    auto_execute_timeout = 60
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
        model=model,
    )


def start_worktree_setup_background(
    issue_key: str,
    branch_prefix: str = "feature",
    branch_name: str | None = None,
    use_existing_branch: bool = False,
    workflow_name: str = "work-on-jira-issue",
    user_request: str | None = None,
    additional_params: dict | None = None,
    auto_execute_command: list[str] | None = None,
    auto_execute_timeout: int = 60,
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
            (default: 60).
        interactive: Whether to start the Copilot session interactively after
            setup (default: False). Set to True for interactive mode.

    Returns:
        The background task ID for tracking progress
    """
    import json

    from ...background_tasks import run_function_in_background
    from ...state import delete_value, get_value, set_value

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
    if auto_execute_timeout != 60:
        set_value("worktree_setup.auto_execute_timeout", str(auto_execute_timeout))
    set_value("worktree_setup.interactive", "true" if interactive else "false")

    # Capture the current model from parent state (correct context at this call site).
    # Always clear any stale worktree_setup.model from a previous run before
    # conditionally storing the current value.
    copilot_model = get_value("copilot.model_id")
    if isinstance(copilot_model, str) and copilot_model.strip():
        set_value("worktree_setup.model", copilot_model.strip())
    else:
        delete_value("worktree_setup.model")

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
    issue_key: str | None = None
    error_message: str | None = None


def create_placeholder_issue(
    project_key: str,
    issue_type: str = "Task",
    parent_key: str | None = None,
) -> PlaceholderIssueResult:
    """
    Create a placeholder Jira issue with minimal fields.

    This creates an issue with a placeholder summary and description
    that will be updated later in the workflow.

    Args:
        project_key: Jira project key (e.g., "PROJECT")
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
    parent_key: str | None = None,
    workflow_name: str = "create-jira-issue",
    user_request: str | None = None,
    additional_params: dict | None = None,
) -> tuple[bool, str | None]:
    """
    Create a placeholder issue and set up a worktree for it.

    This is the main entry point for create workflows that need both
    issue creation and environment setup.

    Args:
        project_key: Jira project key (e.g., "PROJECT")
        issue_type: Issue type (Task, Epic, Sub-task)
        parent_key: Parent issue key (required for Sub-task type)
        workflow_name: Name of the workflow for continuation prompt
        user_request: The user's explanation of what they want to create
            (AI will use this to populate Jira fields appropriately)
        additional_params: Additional parameters to include in the continuation
            command (e.g., {"parent_key": "PROJECT-1234"})

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
