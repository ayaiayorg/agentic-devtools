"""
PR workflow orchestration for agdt-setup.

When ``agdt-setup`` modifies repository files, this module isolates those
changes on a dedicated ``chore/agdt-setup-{version}`` branch, commits them,
pushes the branch, and creates a pull request.  The user's original branch
and any stashed changes are always restored—even when errors occur.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable

from typing_extensions import TypedDict

from agentic_devtools.cli.git.core import run_git


class PrWorkflowResult(TypedDict):
    """Result of the PR workflow orchestration."""

    success: bool
    branch_created: str | None
    pr_created: bool
    message: str


_MAX_BRANCH_SUFFIX_ATTEMPTS = 10


def _resolve_branch_name(version: str) -> str:
    """Return a unique ``chore/agdt-setup-{version}`` branch name.

    Checks both local refs and the remote for collisions and appends
    ``-2``, ``-3``, … until an unused name is found.  Gives up after
    :data:`_MAX_BRANCH_SUFFIX_ATTEMPTS` and falls back to a
    timestamp-based suffix to guarantee termination (e.g. when
    ``git ls-remote`` keeps failing due to network/auth issues).
    """
    base = f"chore/agdt-setup-{version}"
    candidate = base

    suffix = 1
    while suffix <= _MAX_BRANCH_SUFFIX_ATTEMPTS:
        # Check local
        local_check = run_git("rev-parse", "--verify", candidate, check=False)
        if local_check.returncode != 0:
            # Not found locally — check remote
            remote_check = run_git("ls-remote", "--heads", "origin", candidate, check=False)
            if remote_check.returncode != 0:
                # ls-remote failed (network/auth) — treat name as taken to be safe
                print(
                    f"Warning: 'git ls-remote' failed for '{candidate}' — skipping this name.",
                    file=sys.stderr,
                )
            elif not remote_check.stdout.strip():
                return candidate

        # Name is taken; try next suffix
        suffix += 1
        candidate = f"{base}-{suffix}"

    # Exhausted all suffix attempts — fall back to a timestamp suffix
    # so agdt-setup can proceed without hanging.
    fallback = f"{base}-{int(time.time())}"
    print(
        f"Warning: Could not find a free branch name after {_MAX_BRANCH_SUFFIX_ATTEMPTS} "
        f"attempts — using timestamp fallback '{fallback}'.",
        file=sys.stderr,
    )
    return fallback


def run_setup_with_pr_workflow(
    setup_fn: Callable[[], None],
    version: str,
) -> PrWorkflowResult:
    """Run *setup_fn* inside a branch-and-PR workflow.

    1. Fetch ``origin/main`` (fallback to normal run on failure).
    2. Stash uncommitted local changes.
    3. Checkout ``origin/main`` detached.
    4. Execute *setup_fn*.
    5. If files changed → create branch, commit, push, open PR.
    6. Restore the user's original branch and pop the stash.

    Returns a :class:`PrWorkflowResult` describing what happened.
    """
    # Step 1 — fetch origin/main
    fetch_result = run_git("fetch", "origin", "main", check=False)
    if fetch_result.returncode != 0:
        print(
            "Warning: 'git fetch origin main' failed — running setup without PR workflow.",
            file=sys.stderr,
        )
        setup_fn()
        return PrWorkflowResult(
            success=True,
            branch_created=None,
            pr_created=False,
            message="Fetch failed; setup ran without PR workflow.",
        )

    # Step 2 — record current branch
    branch_result = run_git("rev-parse", "--abbrev-ref", "HEAD", check=False)
    original_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    if not original_branch or original_branch == "HEAD":
        print(
            "Warning: Detached HEAD detected — running setup without PR workflow.",
            file=sys.stderr,
        )
        setup_fn()
        return PrWorkflowResult(
            success=True,
            branch_created=None,
            pr_created=False,
            message="Detached HEAD; setup ran without PR workflow.",
        )

    # Step 3 — stash local changes
    stash_list_before = run_git("stash", "list", check=False)
    before_count = len(stash_list_before.stdout.strip().splitlines()) if stash_list_before.stdout.strip() else 0

    stash_push = run_git("stash", "push", "--include-untracked", "-m", "agdt-setup: auto-stash", check=False)
    if stash_push.returncode != 0:
        # Stashing can fail during an in-progress merge/rebase.  Fall back
        # to running setup without the PR workflow so we don't risk
        # detaching HEAD with a dirty/conflicted working tree.
        stash_err = stash_push.stderr.strip()
        print(
            f"Warning: 'git stash push' failed{f': {stash_err}' if stash_err else ''} "
            "— running setup without PR workflow.",
            file=sys.stderr,
        )
        setup_fn()
        return PrWorkflowResult(
            success=True,
            branch_created=None,
            pr_created=False,
            message="Stash failed; setup ran without PR workflow.",
        )

    stash_list_after = run_git("stash", "list", check=False)
    after_count = len(stash_list_after.stdout.strip().splitlines()) if stash_list_after.stdout.strip() else 0
    did_stash = after_count > before_count

    branch_created: str | None = None
    pr_created = False
    message = "No file changes detected."
    emergency_stash_created = False

    try:
        # Step 4 — checkout origin/main detached
        checkout_result = run_git("checkout", "origin/main", "--detach", check=False)
        if checkout_result.returncode != 0:
            print(
                "Warning: Could not checkout origin/main — running setup on current branch.",
                file=sys.stderr,
            )
            setup_fn()
            return PrWorkflowResult(
                success=True,
                branch_created=None,
                pr_created=False,
                message="Could not checkout origin/main; setup ran on current branch.",
            )

        # Step 5 — run setup
        setup_fn()

        # Step 6 — check for changes
        status_result = run_git("status", "--porcelain", check=False)
        has_changes = bool(status_result.stdout.strip())

        if has_changes:
            # Step 7 — create branch, commit, push
            # All git operations use check=False because the PR workflow is
            # best-effort: a failure here must not terminate agdt-setup.
            branch_name = _resolve_branch_name(version)
            create_branch = run_git("checkout", "-b", branch_name, check=False)
            if create_branch.returncode != 0:
                print(
                    f"Error: Could not create branch '{branch_name}': {create_branch.stderr.strip()}",
                    file=sys.stderr,
                )
                message = f"Failed to create branch '{branch_name}'."
            else:
                commit_msg = f"chore: agdt-setup v{version}"
                add_result = run_git("add", ".", check=False)
                if add_result.returncode != 0:
                    print(
                        f"Error: 'git add .' failed: {add_result.stderr.strip()}",
                        file=sys.stderr,
                    )
                    message = "Failed to stage changes."
                else:
                    commit_result = run_git("commit", "-m", commit_msg, check=False)
                    if commit_result.returncode != 0:
                        print(
                            f"Error: 'git commit' failed: {commit_result.stderr.strip()}",
                            file=sys.stderr,
                        )
                        message = "Failed to commit changes."
                    else:
                        branch_created = branch_name

                        push_result = run_git("push", "--set-upstream", "origin", branch_name, check=False)
                        if push_result.returncode != 0:
                            print(
                                f"Error: Failed to push branch '{branch_name}': {push_result.stderr.strip()}",
                                file=sys.stderr,
                            )
                            message = f"Branch '{branch_name}' created and committed but push failed."
                        else:
                            # Step 8 — create PR synchronously
                            try:
                                from agentic_devtools.cli.azure_devops.commands import (
                                    create_pull_request,
                                )
                                from agentic_devtools.state import set_value

                                pr_title = f"chore: agdt-setup v{version}"
                                set_value("source_branch", branch_name)
                                set_value("title", pr_title)
                                set_value("draft", "false")

                                create_pull_request()
                                pr_created = True
                                message = f"PR created from branch '{branch_name}'."
                            except SystemExit as exc:
                                # create_pull_request() calls sys.exit() on
                                # validation/az failures — treat as non-fatal.
                                print(
                                    f"Warning: PR creation failed ({exc}) — branch '{branch_name}' was pushed.",
                                    file=sys.stderr,
                                )
                                message = f"Branch '{branch_name}' pushed but PR creation failed."
                            except Exception as exc:  # noqa: BLE001
                                print(
                                    f"Warning: PR creation failed ({exc}) — branch '{branch_name}' was pushed.",
                                    file=sys.stderr,
                                )
                                message = f"Branch '{branch_name}' pushed but PR creation failed."
    finally:
        # Step 12 — restore original branch
        restore = run_git("checkout", original_branch, check=False)
        if restore.returncode != 0:
            # The checkout may have failed because setup_fn() left
            # uncommitted changes in the working tree (e.g. when
            # checkout -b / add / commit failed partway through).
            # Stash those changes and retry so the user gets back to
            # their original branch.
            emergency_stash = run_git(
                "stash",
                "push",
                "--include-untracked",
                "-m",
                "agdt-setup: uncommitted changes blocking branch restore",
                check=False,
            )
            if emergency_stash.returncode == 0:
                emergency_stash_created = True
                retry = run_git("checkout", original_branch, check=False)
                if retry.returncode == 0:
                    print(
                        f"Warning: Uncommitted setup changes were stashed to restore "
                        f"branch '{original_branch}'. Run 'git stash list' to see them.",
                        file=sys.stderr,
                    )
                else:
                    print(
                        f"Warning: Could not restore branch '{original_branch}' "
                        f"even after stashing uncommitted changes. "
                        f"Run 'git checkout {original_branch}' manually.",
                        file=sys.stderr,
                    )
            else:
                print(
                    f"Warning: Could not restore branch '{original_branch}'. "
                    f"Run 'git checkout {original_branch}' manually.",
                    file=sys.stderr,
                )

        # Step 13 — pop the user's original auto-stash.
        # If an emergency stash was created above (to unblock branch
        # restore), it sits at stash@{0} and the user's auto-stash has
        # been pushed down to stash@{1}.  We must pop the correct entry.
        if did_stash:
            stash_ref = "stash@{0}"
            if emergency_stash_created:
                stash_ref = "stash@{1}"
            pop_result = run_git("stash", "pop", stash_ref, check=False)
            if pop_result.returncode != 0:
                print(
                    "Warning: Could not auto-restore stashed changes. "
                    "Your changes are still saved in git stash. "
                    "Run 'git stash list' to see them and 'git stash pop' to restore manually.",
                    file=sys.stderr,
                )

    return PrWorkflowResult(
        success=True,
        branch_created=branch_created,
        pr_created=pr_created,
        message=message,
    )
