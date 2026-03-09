"""``agdt-review status`` — show multi-model review progress for a PR."""

from agentic_devtools.cli.azure_devops.review_attribution import (
    format_status,
    should_use_emoji,
)


def run_status(pr_id: int) -> None:
    """Display multi-model review progress.

    Shows which reviewers are done, which are pending, which files need
    consolidation, and the consolidation status.

    .. note::
        This is a **stub** — in production, it reads ``review-state.json``
        and the review config to build the status display.

    Args:
        pr_id: Pull request ID.
    """
    use_emoji = should_use_emoji()

    print("=" * 60)
    print(f"REVIEW STATUS — PR {pr_id}")
    print("=" * 60)
    # TODO: Wire to review state loading and render the actual status table.
    # In production this would:
    # 1. Load review-state.json for the PR
    # 2. Load the review config
    # 3. Show reviewer completion status per-model
    # 4. Show per-file consolidation status
    # 5. Show overall PR status
    print(f"Overall: {format_status('in-progress', use_emoji=use_emoji)}")
    print()
    print("(Status display is a stub — wire to review state in production)")
