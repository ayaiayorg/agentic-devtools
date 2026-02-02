"""
Git operations for CLI commands.

This module provides the individual git operations:
- Staging changes
- Creating/amending commits
- Pushing/publishing branches
- Branch state detection
"""

from typing import Optional

from .core import get_current_branch, run_git, temp_message_file


def stage_changes(dry_run: bool) -> None:
    """
    Stage all changes (git add .).

    Args:
        dry_run: If True, only print what would happen
    """
    if dry_run:
        print("[DRY RUN] Would stage all changes (git add .)")
        return

    print("Staging all changes...")
    run_git("add", ".")
    print("Changes staged.")


def create_commit(message: str, dry_run: bool) -> None:
    """
    Create a commit with the given message.

    Uses a temp file to handle multiline messages safely across platforms.

    Args:
        message: The commit message
        dry_run: If True, only print what would happen
    """
    if dry_run:
        print("[DRY RUN] Would create commit with message:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        return

    print("Creating commit...")

    with temp_message_file(message) as temp_path:
        run_git("commit", "-F", temp_path)

    print("Commit created successfully.")


def amend_commit(message: str, dry_run: bool) -> None:
    """
    Amend the current commit with a new message.

    Uses a temp file to handle multiline messages safely across platforms.

    Args:
        message: The new commit message
        dry_run: If True, only print what would happen
    """
    if dry_run:
        print("[DRY RUN] Would amend commit with message:")
        print("-" * 40)
        print(message)
        print("-" * 40)
        return

    print("Amending commit...")

    with temp_message_file(message) as temp_path:
        run_git("commit", "--amend", "-F", temp_path)

    print("Commit amended successfully.")


def publish_branch(dry_run: bool) -> None:
    """
    Push and set upstream for the current branch.

    Args:
        dry_run: If True, only print what would happen
    """
    branch = get_current_branch()

    if dry_run:
        print(f"[DRY RUN] Would publish branch '{branch}' (git push --set-upstream origin {branch})")
        return

    print(f"Publishing branch '{branch}'...")
    run_git("push", "--set-upstream", "origin", branch)
    print("Branch published successfully.")


def force_push(dry_run: bool) -> None:
    """
    Force push with lease (safe force push).

    Uses --force-with-lease to prevent overwriting others' changes.

    Args:
        dry_run: If True, only print what would happen
    """
    if dry_run:
        print("[DRY RUN] Would force push (git push --force-with-lease)")
        return

    print("Force pushing changes...")
    run_git("push", "--force-with-lease")
    print("Changes pushed successfully.")


def push(dry_run: bool) -> None:
    """
    Push to remote (regular push).

    Args:
        dry_run: If True, only print what would happen
    """
    if dry_run:
        print("[DRY RUN] Would push changes (git push)")
        return

    print("Pushing changes...")
    run_git("push")
    print("Changes pushed successfully.")


def get_last_commit_message() -> Optional[str]:
    """
    Get the message of the last commit on the current branch.

    Returns:
        The commit message, or None if no commits exist
    """
    result = run_git("log", "-1", "--format=%B", check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def branch_has_commits_ahead_of_main(main_branch: str = "main") -> bool:
    """
    Check if the current branch has commits ahead of the main branch.

    Args:
        main_branch: Name of the main branch (default: "main")

    Returns:
        True if current branch has commits not in main
    """
    current = get_current_branch()
    if current == main_branch:
        return False

    # Check if main branch exists
    result = run_git("rev-parse", "--verify", f"origin/{main_branch}", check=False)
    if result.returncode != 0:
        # Try without origin/
        result = run_git("rev-parse", "--verify", main_branch, check=False)
        if result.returncode != 0:
            return False
        ref = main_branch
    else:
        ref = f"origin/{main_branch}"

    # Count commits ahead
    result = run_git("rev-list", "--count", f"{ref}..HEAD", check=False)
    if result.returncode != 0:
        return False

    try:
        count = int(result.stdout.strip())
        return count > 0
    except ValueError:
        return False


def last_commit_contains_issue_key(issue_key: str) -> bool:
    """
    Check if the last commit message contains the given issue key.

    Args:
        issue_key: The Jira issue key to look for (e.g., "DFLY-1234")

    Returns:
        True if the last commit message contains the issue key
    """
    message = get_last_commit_message()
    if not message:
        return False
    return issue_key.upper() in message.upper()


def should_amend_instead_of_commit(issue_key: Optional[str] = None) -> bool:
    """
    Determine if we should amend the existing commit instead of creating a new one.

    Logic:
    - If branch has commits ahead of main → amend (single-commit policy)
    - If branch has no commits ahead of main → new commit

    The issue_key parameter is kept for API compatibility but no longer affects
    the decision. We always amend when there are existing commits to maintain
    a clean single-commit-per-feature history.

    Args:
        issue_key: Optional Jira issue key (kept for API compatibility, not used)

    Returns:
        True if should amend, False if should create new commit
    """
    # Has commits ahead of main → always amend (single-commit policy)
    # No commits ahead of main → new commit
    return branch_has_commits_ahead_of_main()


def has_local_changes() -> bool:
    """
    Check if there are any local changes (staged or unstaged).

    Returns:
        True if there are uncommitted changes
    """
    # Check for staged changes
    result = run_git("diff", "--cached", "--quiet", check=False)
    if result.returncode != 0:
        return True

    # Check for unstaged changes
    result = run_git("diff", "--quiet", check=False)
    if result.returncode != 0:
        return True

    # Check for untracked files
    result = run_git("ls-files", "--others", "--exclude-standard", check=False)
    if result.returncode == 0 and result.stdout.strip():
        return True

    return False


def local_branch_matches_origin() -> bool:
    """
    Check if the local branch matches the origin branch (no unpushed commits).

    Returns:
        True if local and origin are in sync
    """
    branch = get_current_branch()

    # Check if origin branch exists
    result = run_git("rev-parse", "--verify", f"origin/{branch}", check=False)
    if result.returncode != 0:
        # Origin branch doesn't exist - not in sync
        return False

    # Compare local and origin
    result = run_git("rev-list", "--count", f"origin/{branch}..HEAD", check=False)
    if result.returncode != 0:
        return False

    try:
        ahead = int(result.stdout.strip())
    except ValueError:
        return False

    result = run_git("rev-list", "--count", f"HEAD..origin/{branch}", check=False)
    if result.returncode != 0:
        return False

    try:
        behind = int(result.stdout.strip())
    except ValueError:
        return False

    return ahead == 0 and behind == 0


class BranchSafetyCheckResult:
    """Result of checking if a branch is safe to recreate/delete."""

    SAFE = "safe"
    UNCOMMITTED_CHANGES = "uncommitted_changes"
    DIVERGED_FROM_ORIGIN = "diverged_from_origin"
    BRANCH_NOT_ON_ORIGIN = "branch_not_on_origin"
    NOT_ON_BRANCH = "not_on_branch"

    def __init__(self, status: str, message: str = "", branch_name: str = ""):
        self.status = status
        self.message = message
        self.branch_name = branch_name

    @property
    def is_safe(self) -> bool:
        """Check if it's safe to proceed with branch operations."""
        return self.status == self.SAFE

    @property
    def has_local_work_at_risk(self) -> bool:
        """Check if there's local work that could be lost."""
        return self.status in (self.UNCOMMITTED_CHANGES, self.DIVERGED_FROM_ORIGIN)


def check_branch_safe_to_recreate(branch_name: str) -> BranchSafetyCheckResult:
    """
    Check if a local branch is safe to delete/recreate.

    This is used before PR review worktree setup to ensure we don't
    destroy local work. A branch is safe to recreate if:
    1. We're currently on that branch (or can switch to it)
    2. There are no uncommitted changes
    3. The local branch matches origin (same commit hash)

    Args:
        branch_name: Name of the branch to check

    Returns:
        BranchSafetyCheckResult indicating whether it's safe to proceed
    """
    # Check if the branch exists locally
    result = run_git("rev-parse", "--verify", branch_name, check=False)
    local_exists = result.returncode == 0

    # Check if the branch exists on origin
    result = run_git("rev-parse", "--verify", f"origin/{branch_name}", check=False)
    origin_exists = result.returncode == 0

    if not local_exists:
        # Branch doesn't exist locally - safe to create from origin
        if origin_exists:
            return BranchSafetyCheckResult(
                BranchSafetyCheckResult.SAFE,
                f"Branch '{branch_name}' doesn't exist locally, will checkout from origin.",
                branch_name,
            )
        else:
            return BranchSafetyCheckResult(
                BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN,
                f"Branch '{branch_name}' doesn't exist locally or on origin.",
                branch_name,
            )

    # Branch exists locally - check if we're on it
    current = get_current_branch()
    if not current:
        return BranchSafetyCheckResult(
            BranchSafetyCheckResult.NOT_ON_BRANCH,
            "Detached HEAD state. Cannot safely check branch status.",
            branch_name,
        )

    # If we're on a different branch, we need to be careful
    if current != branch_name:
        # Check for uncommitted changes on current branch first
        if has_local_changes():
            return BranchSafetyCheckResult(
                BranchSafetyCheckResult.UNCOMMITTED_CHANGES,
                f"You have uncommitted changes on branch '{current}'.\n"
                f"Please commit, stash, or discard them before proceeding.",
                branch_name,
            )

        # We'd need to switch branches - check if target branch is safe
        # Get local and origin commits for target branch
        local_commit = run_git("rev-parse", branch_name, check=False)
        origin_commit = run_git("rev-parse", f"origin/{branch_name}", check=False)

        if local_commit.returncode != 0:
            return BranchSafetyCheckResult(
                BranchSafetyCheckResult.NOT_ON_BRANCH,
                f"Cannot determine commit for local branch '{branch_name}'.",
                branch_name,
            )

        if origin_commit.returncode != 0:
            return BranchSafetyCheckResult(
                BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN,
                f"Branch '{branch_name}' exists locally but not on origin.\nLocal work may be lost if we proceed.",
                branch_name,
            )

        if local_commit.stdout.strip() != origin_commit.stdout.strip():
            return BranchSafetyCheckResult(
                BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
                f"Local branch '{branch_name}' has diverged from origin.\n"
                f"Local commits may be lost if we proceed.\n"
                f"Please push your local changes first, or use a different worktree.",
                branch_name,
            )

        return BranchSafetyCheckResult(
            BranchSafetyCheckResult.SAFE,
            f"Branch '{branch_name}' is safe to use.",
            branch_name,
        )

    # We're on the target branch - check for uncommitted changes
    if has_local_changes():
        return BranchSafetyCheckResult(
            BranchSafetyCheckResult.UNCOMMITTED_CHANGES,
            f"You have uncommitted changes on branch '{branch_name}'.\n"
            f"Please commit, stash, or discard them before proceeding.",
            branch_name,
        )

    # Check if local matches origin
    if not origin_exists:
        return BranchSafetyCheckResult(
            BranchSafetyCheckResult.BRANCH_NOT_ON_ORIGIN,
            f"Branch '{branch_name}' exists locally but not on origin.\nLocal work may be lost if we proceed.",
            branch_name,
        )

    local_commit = run_git("rev-parse", "HEAD", check=False)
    origin_commit = run_git("rev-parse", f"origin/{branch_name}", check=False)

    if local_commit.returncode != 0 or origin_commit.returncode != 0:
        return BranchSafetyCheckResult(
            BranchSafetyCheckResult.NOT_ON_BRANCH,
            "Cannot determine commit hashes for comparison.",
            branch_name,
        )

    if local_commit.stdout.strip() != origin_commit.stdout.strip():
        return BranchSafetyCheckResult(
            BranchSafetyCheckResult.DIVERGED_FROM_ORIGIN,
            f"Local branch '{branch_name}' has diverged from origin.\n"
            f"Local commits may be lost if we proceed.\n"
            f"Please push your local changes first.",
            branch_name,
        )

    return BranchSafetyCheckResult(
        BranchSafetyCheckResult.SAFE,
        f"Branch '{branch_name}' is in sync with origin and safe to use.",
        branch_name,
    )


def fetch_branch(branch_name: str, dry_run: bool = False) -> bool:
    """
    Fetch a specific branch from origin.

    Args:
        branch_name: Name of the branch to fetch
        dry_run: If True, only print what would happen

    Returns:
        True if fetch succeeded, False otherwise
    """
    if dry_run:
        print(f"[DRY RUN] Would fetch origin/{branch_name}")
        return True

    print(f"Fetching origin/{branch_name}...")
    result = run_git("fetch", "origin", branch_name, check=False)
    if result.returncode != 0:
        print(f"Warning: Failed to fetch origin/{branch_name}")
        if result.stderr:
            print(result.stderr.strip())
        return False

    print(f"Fetched origin/{branch_name} successfully.")
    return True


def fetch_main(main_branch: str = "main", dry_run: bool = False) -> bool:
    """
    Fetch the latest from origin for the main branch.

    Args:
        main_branch: Name of the main branch (default: "main")
        dry_run: If True, only print what would happen

    Returns:
        True if fetch succeeded, False otherwise
    """
    if dry_run:
        print(f"[DRY RUN] Would fetch origin/{main_branch}")
        return True

    print(f"Fetching latest from origin/{main_branch}...")
    result = run_git("fetch", "origin", main_branch, check=False)
    if result.returncode != 0:
        print(f"Warning: Failed to fetch origin/{main_branch}")
        if result.stderr:
            print(result.stderr.strip())
        return False

    print(f"Fetched origin/{main_branch} successfully.")
    return True


def get_commits_behind_main(main_branch: str = "main") -> int:
    """
    Get the number of commits the current branch is behind origin/main.

    Args:
        main_branch: Name of the main branch (default: "main")

    Returns:
        Number of commits behind, or 0 if unable to determine
    """
    result = run_git("rev-list", "--count", f"HEAD..origin/{main_branch}", check=False)
    if result.returncode != 0:
        return 0

    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


class RebaseResult:
    """Result of a rebase operation."""

    SUCCESS = "success"
    NO_REBASE_NEEDED = "no_rebase_needed"
    CONFLICT = "conflict"
    ERROR = "error"

    def __init__(self, status: str, message: str = ""):
        self.status = status
        self.message = message

    @property
    def is_success(self) -> bool:
        return self.status in (self.SUCCESS, self.NO_REBASE_NEEDED)

    @property
    def was_rebased(self) -> bool:
        """Return True if a rebase actually occurred (history was rewritten)."""
        return self.status == self.SUCCESS

    @property
    def needs_manual_resolution(self) -> bool:
        return self.status == self.CONFLICT


def rebase_onto_main(main_branch: str = "main", dry_run: bool = False) -> RebaseResult:
    """
    Rebase the current branch onto origin/main if there are new commits.

    This performs a non-interactive rebase. If conflicts occur, the rebase
    is automatically aborted and the user is instructed to resolve manually.

    Args:
        main_branch: Name of the main branch (default: "main")
        dry_run: If True, only print what would happen

    Returns:
        RebaseResult indicating success, no rebase needed, conflict, or error
    """
    # Check how many commits we're behind
    commits_behind = get_commits_behind_main(main_branch)

    if commits_behind == 0:
        print(f"Branch is already up-to-date with origin/{main_branch}.")
        return RebaseResult(RebaseResult.NO_REBASE_NEEDED)

    if dry_run:
        print(f"[DRY RUN] Would rebase onto origin/{main_branch} ({commits_behind} commits behind)")
        return RebaseResult(RebaseResult.SUCCESS)

    print(f"Rebasing onto origin/{main_branch} ({commits_behind} commits behind)...")

    # Perform rebase (non-interactive, no editor)
    result = run_git(
        "rebase",
        f"origin/{main_branch}",
        check=False,
    )

    if result.returncode == 0:
        print("Rebase completed successfully.")
        return RebaseResult(RebaseResult.SUCCESS)

    # Rebase failed - check if it's a conflict
    if "conflict" in result.stdout.lower() or "conflict" in result.stderr.lower():
        # Abort the rebase
        print("Rebase conflicts detected. Aborting rebase...")
        abort_result = run_git("rebase", "--abort", check=False)

        if abort_result.returncode != 0:
            return RebaseResult(
                RebaseResult.ERROR,
                "Failed to abort rebase. Manual intervention required.",
            )

        return RebaseResult(
            RebaseResult.CONFLICT,
            f"Rebase onto origin/{main_branch} resulted in conflicts.\n"
            f"Please resolve manually by either:\n"
            f"  1. Rebase: git fetch origin {main_branch} && git rebase origin/{main_branch}\n"
            f"     Then resolve conflicts and continue with: git rebase --continue\n"
            f"  2. Merge: git fetch origin {main_branch} && git merge origin/{main_branch}\n"
            f"     Then resolve conflicts if any and commit the merge.",
        )

    # Some other error
    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
    # Try to abort in case rebase is in progress
    run_git("rebase", "--abort", check=False)

    return RebaseResult(RebaseResult.ERROR, f"Rebase failed: {error_msg}")


class CheckoutResult:
    """Result of a checkout operation."""

    SUCCESS = "success"
    UNCOMMITTED_CHANGES = "uncommitted_changes"
    BRANCH_NOT_FOUND = "branch_not_found"
    ERROR = "error"

    def __init__(self, status: str, message: str = ""):
        self.status = status
        self.message = message

    @property
    def is_success(self) -> bool:
        return self.status == self.SUCCESS

    @property
    def needs_user_action(self) -> bool:
        return self.status in (self.UNCOMMITTED_CHANGES, self.BRANCH_NOT_FOUND)


def checkout_branch(branch_name: str, dry_run: bool = False) -> CheckoutResult:
    """
    Checkout a git branch.

    Args:
        branch_name: Name of the branch to checkout
        dry_run: If True, only print what would happen

    Returns:
        CheckoutResult indicating success or the type of failure
    """
    from .core import get_current_branch

    # Check if already on the branch
    try:
        current = get_current_branch()
        if current == branch_name:
            print(f"Already on branch '{branch_name}'")
            return CheckoutResult(CheckoutResult.SUCCESS)
    except SystemExit:
        pass  # Could be detached HEAD, continue with checkout

    if dry_run:
        print(f"[DRY RUN] Would checkout branch '{branch_name}'")
        return CheckoutResult(CheckoutResult.SUCCESS)

    # Check for uncommitted changes first
    if has_local_changes():
        return CheckoutResult(
            CheckoutResult.UNCOMMITTED_CHANGES,
            f"Cannot checkout branch '{branch_name}' - you have uncommitted changes.\n"
            f"Please either:\n"
            f"  1. Commit your changes: agdt-git-commit\n"
            f"  2. Stash your changes: git stash\n"
            f"  3. Discard changes: git checkout -- . && git clean -fd\n"
            f"Then restart the workflow.",
        )

    print(f"Checking out branch '{branch_name}'...")

    # First try to checkout existing local branch
    result = run_git("checkout", branch_name, check=False)

    if result.returncode == 0:
        print(f"Checked out branch '{branch_name}' successfully.")
        return CheckoutResult(CheckoutResult.SUCCESS)

    # If local doesn't exist, try to checkout from origin
    result = run_git("checkout", "-b", branch_name, f"origin/{branch_name}", check=False)

    if result.returncode == 0:
        print(f"Checked out branch '{branch_name}' from origin.")
        return CheckoutResult(CheckoutResult.SUCCESS)

    # Branch not found
    error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()

    if "did not match any" in error_msg.lower() or "not found" in error_msg.lower():
        return CheckoutResult(
            CheckoutResult.BRANCH_NOT_FOUND,
            f"Branch '{branch_name}' not found locally or on origin.\nPlease verify the branch name is correct.",
        )

    return CheckoutResult(CheckoutResult.ERROR, f"Checkout failed: {error_msg}")


def get_files_changed_on_branch(main_branch: str = "main") -> list[str]:
    """
    Get the list of files that have been changed on the current branch vs main.

    This returns files that are in commits ahead of main, not including
    files from recently merged PRs or other changes on main.

    Args:
        main_branch: Name of the main branch (default: "main")

    Returns:
        List of file paths (normalized with forward slashes)
    """
    # Use diff to get files changed between origin/main and HEAD
    result = run_git(
        "diff",
        "--name-only",
        f"origin/{main_branch}...HEAD",
        check=False,
    )

    if result.returncode != 0:
        # Fallback: try without origin prefix
        result = run_git(
            "diff",
            "--name-only",
            f"{main_branch}...HEAD",
            check=False,
        )

    if result.returncode != 0:
        print(f"Warning: Could not determine files changed vs {main_branch}")
        return []

    files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    # Normalize paths to use forward slashes
    return [f.replace("\\", "/") for f in files if f.strip()]
