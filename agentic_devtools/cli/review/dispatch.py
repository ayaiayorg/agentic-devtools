"""``agdt-review dispatch`` — multi-model review orchestrator.

Reads the review configuration, iterates through reviewers in order,
and conditionally triggers consolidation per-file when amendment replies
exist.
"""

import logging
import sys

from agentic_devtools.cli.azure_devops.review_attribution import (
    format_status,
    should_use_emoji,
)
from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfig,
    ReviewConfigError,
    load_review_config,
    resolve_trigger_overrides,
)
from agentic_devtools.cli.review.config_commands import _resolve_repo_root

logger = logging.getLogger(__name__)

_MAX_REVIEWER_RETRIES = 3
_MAX_CONSOLIDATOR_RETRIES = 5


def _print_dispatch_plan(config: ReviewConfig, pr_id: int, label: str) -> None:
    """Print the dispatch plan for a dry-run."""
    use_emoji = should_use_emoji()
    print("=" * 60)
    print("DISPATCH PLAN (dry-run)")
    print("=" * 60)
    print(f"PR ID:  {pr_id}")
    print(f"Label:  {label}")
    print(f"Status: {format_status('in-progress', use_emoji=use_emoji)}")
    print()
    print("Reviewers (in order):")
    for i, rev in enumerate(config.reviewers, 1):
        print(f"  {i}. {rev.model_id} (role: {rev.role})")
    print()
    if config.consolidation and not config.skip_consolidation:
        print(f"Consolidator: {config.consolidation.model_id}")
        print("  Triggered only when amendment replies exist per-file.")
    elif config.skip_consolidation:
        print("Consolidation: SKIPPED (skip_consolidation=true)")
        print(f"  Mechanical consensus strategy: {config.consensus.strategy}")
    else:
        print("Consolidation: not configured")
    print()
    print(f"Consensus strategy: {config.consensus.strategy} (advisory)")
    print(f"Min reviewers: {config.consensus.min_reviewers}")
    print(f"Max reviewers: {config.consensus.max_reviewers}")
    print()
    if config.file_filters.include:
        print(f"Include patterns: {config.file_filters.include}")
    if config.file_filters.exclude:
        print(f"Exclude patterns: {config.file_filters.exclude}")


def _invoke_reviewer(
    pr_id: int,
    model_id: str,
    role: str,
    retry_count: int = _MAX_REVIEWER_RETRIES,
    *,
    use_emoji: bool = False,
) -> bool:
    """Invoke a reviewer model for the PR.

    Returns True on success, False if the reviewer is unavailable after retries.

    .. note::
        This is a **stub** — the actual invocation of
        ``agdt-review-pull-request --model-id X --role reviewer`` is not
        yet wired. Only the function signature and configuration constants
        are in place; the retry/backoff/exception-handling logic is still TODO.

    When wired to the real implementation, this function will:
    1. Call the review function with ``model_id`` and ``role``.
    2. On failure, retry ``retry_count`` times with exponential backoff.
    3. Return False if all retries are exhausted.
    """
    # TODO: Wire to actual review invocation (call the Python function that
    # agdt-review-pull-request wraps, passing model_id and role parameters).
    # Replace the stub below with try/except retry logic.
    logger.info(
        "Invoking reviewer %s (role=%s) for PR %d (retry_count=%d)",
        model_id,
        role,
        pr_id,
        retry_count,
    )
    # Stub: simulate success
    ok_mark = "✓" if use_emoji else "[OK]"
    print(f"  {ok_mark} Reviewer {model_id} ({role}) completed for PR {pr_id}")
    return True


def _invoke_consolidation(
    pr_id: int,
    model_id: str,
    retry_count: int = _MAX_CONSOLIDATOR_RETRIES,
    *,
    use_emoji: bool = False,
) -> bool:
    """Invoke consolidation for the PR.

    Returns True on success, False if the consolidator is unavailable.

    .. note::
        This is a **stub** — the actual invocation of
        ``agdt-review consolidate`` is not yet wired.

    When wired to the real implementation, this function will:
    1. Call the consolidation function with ``model_id``.
    2. On failure, retry ``retry_count`` times with exponential backoff
       (more aggressive than reviewers — conflict resolution is critical).
    3. Return False if all retries are exhausted.
    """
    # TODO: Wire to actual consolidation invocation.
    # Replace the stub below with try/except retry logic.
    logger.info(
        "Invoking consolidator %s for PR %d (retry_count=%d)",
        model_id,
        pr_id,
        retry_count,
    )
    # Stub: simulate success
    ok_mark = "✓" if use_emoji else "[OK]"
    print(f"  {ok_mark} Consolidator {model_id} completed for PR {pr_id}")
    return True


def _check_files_need_consolidation(pr_id: int) -> list[str]:
    """Return list of file paths that need consolidation.

    .. note::
        This is a **stub** — in production this reads ``review-state.json``
        and checks ``FileEntry.needs_consolidation()`` per file.
    """
    # TODO: Wire to review state loading and per-file consolidation check.
    logger.info("Checking files needing consolidation for PR %d", pr_id)
    return []


def run_dispatch(
    pr_id: int,
    label: str,
    config_path: str | None = None,
    dry_run: bool = False,
) -> None:
    """Execute the multi-model review dispatch.

    Args:
        pr_id: Pull request ID.
        label: PR label that triggered the review.
        config_path: Optional override — either a repository root directory
            or a path to the ``.agdt/review-config.yaml`` or
            ``.agdt/review-config.yml`` file.
        dry_run: If True, print plan without executing.
    """
    try:
        repo_root = _resolve_repo_root(config_path)
    except ReviewConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    use_emoji = should_use_emoji()

    try:
        config = load_review_config(repo_root)
    except ReviewConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        config = resolve_trigger_overrides(config, label)
    except ReviewConfigError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        _print_dispatch_plan(config, pr_id, label)
        return

    print("=" * 60)
    print(f"MULTI-MODEL REVIEW DISPATCH — PR {pr_id}")
    print(f"Status: {format_status('in-progress', use_emoji=use_emoji)}")
    print("=" * 60)

    # Phase 1: Dispatch reviewers sequentially
    completed_reviewers: list[str] = []
    skipped_reviewers: list[str] = []

    for rev in config.reviewers:
        success = _invoke_reviewer(pr_id, rev.model_id, rev.role, use_emoji=use_emoji)
        if success:
            completed_reviewers.append(rev.model_id)
        else:
            skipped_reviewers.append(rev.model_id)
            warn_mark = "⚠" if use_emoji else "[WARN]"
            print(
                f"  {warn_mark} Reviewer {rev.model_id} unavailable after retries, skipping.",
                file=sys.stderr,
            )

    if not completed_reviewers:
        print("Error: No reviewers completed successfully.", file=sys.stderr)
        sys.exit(1)

    print()
    print(f"Reviewers completed: {len(completed_reviewers)}/{len(config.reviewers)}")
    if skipped_reviewers:
        print(f"Reviewers skipped:   {skipped_reviewers}")

    # Phase 2: Check per-file consolidation need
    files_needing_consolidation = _check_files_need_consolidation(pr_id)

    if files_needing_consolidation and config.consolidation and not config.skip_consolidation:
        print()
        print(f"Files needing consolidation: {len(files_needing_consolidation)}")
        consolidator_model = config.consolidation.model_id
        success = _invoke_consolidation(pr_id, consolidator_model, use_emoji=use_emoji)
        if not success:
            # Fall back to mechanical consensus
            warn_mark = "⚠" if use_emoji else "[WARN]"
            print(
                f"  {warn_mark} Consolidation skipped — {consolidator_model} unavailable. "
                f"Final verdict determined by {config.consensus.strategy} consensus.",
                file=sys.stderr,
            )
    elif files_needing_consolidation and config.skip_consolidation:
        print()
        print(
            f"Consolidation skipped (skip_consolidation=true). "
            f"Using mechanical consensus ({config.consensus.strategy})."
        )
    elif files_needing_consolidation and not config.consolidation:
        warn_mark = "⚠" if use_emoji else "[WARN]"
        print(
            f"  {warn_mark} Consolidation not configured but {len(files_needing_consolidation)} "
            f"file(s) have conflicting reviews. "
            f"Using mechanical consensus ({config.consensus.strategy}).",
            file=sys.stderr,
        )

    print()
    # TODO: Replace with actual terminal status from review results.
    print(f"Final status: {format_status('in-progress', use_emoji=use_emoji)}")
    print("Dispatch complete (stub).")
