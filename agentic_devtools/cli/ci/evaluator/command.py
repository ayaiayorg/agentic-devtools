"""CLI command for the post-agent evaluator.

Provides ``evaluate_post_agent_state_command()`` which is the entry point
for ``agdt-evaluate-post-agent-state``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

from ....state import get_value, set_value
from ...github.repo_resolution import resolve_github_repo
from ..github_provider import GitHubActionsProvider
from .actions import dispatch_action
from .classifier import classify_post_agent_state
from .lock import acquire_lock, release_lock
from .snapshot import build_snapshot

logger = logging.getLogger(__name__)


def evaluate_post_agent_state_command() -> None:
    """CLI entry point for the post-agent evaluator.

    Gathers PR state, classifies it, and dispatches the appropriate
    remediation action. Outputs structured JSON to stdout.

    CLI args:
        --pr: Pull request number (overrides state).
        --repo: Repository (owner/repo) (overrides state).
        --dry-run: Preview without executing side effects.
    """
    parser = argparse.ArgumentParser(
        description="Evaluate PR state after a Copilot agent session",
    )
    parser.add_argument("--pr", type=int, default=None, help="Pull request number")
    parser.add_argument("--repo", type=str, default=None, help="Repository (owner/repo)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without side effects")

    args = parser.parse_args()

    # Resolve PR number
    pr_number = args.pr or get_value("github.pull_request_number")
    if not pr_number:
        print("Error: --pr required or set github.pull_request_number", file=sys.stderr)
        sys.exit(1)
    pr_number = int(pr_number)

    repo = resolve_github_repo(args.repo)

    dry_run = args.dry_run

    # Create provider
    provider = GitHubActionsProvider(repo=repo)

    # Acquire lock (skip in dry-run mode)
    lock_token: str | None = None
    if not dry_run:
        lock_token = acquire_lock(provider, pr_number)
        if lock_token is None:
            # Another evaluator holds the lock
            lock_result = {
                "classification": "concurrent_evaluation_skipped",
                "action_taken": "no_action",
                "success": True,
                "threads_resolved": 0,
                "threads_unresolved": 0,
                "error_details": None,
                "dry_run": False,
            }
            print(json.dumps(lock_result, indent=2))
            set_value("evaluator.classification", "concurrent_evaluation_skipped")
            set_value("evaluator.action_taken", "no_action")
            set_value("evaluator.success", True)
            sys.exit(0)

    try:
        # Build snapshot
        snapshot = build_snapshot(provider, pr_number, repo, current_lock_token=lock_token)

        # Classify
        classification = classify_post_agent_state(snapshot)
        logger.info("PR #%d classified as: %s", pr_number, classification.value)

        # Dispatch action
        evaluation_result = dispatch_action(classification, provider, snapshot, dry_run=dry_run)

        # Write state
        set_value("evaluator.classification", evaluation_result.classification.value)
        set_value("evaluator.action_taken", evaluation_result.action_taken.value)
        set_value("evaluator.success", evaluation_result.success)

        # Output JSON
        print(json.dumps(evaluation_result.to_dict(), indent=2))

        if not evaluation_result.success:
            sys.exit(1)

    finally:
        # Release lock
        if lock_token and not dry_run:
            try:
                release_lock(provider, pr_number, lock_token)
            except Exception:
                logger.warning("Failed to release lock for PR #%d", pr_number)
