"""
Pull Request Summary Commands (deprecated).

This module is retained only for backward compatibility. The legacy flow
that generated overarching PR review comments has been removed. PR summaries
are now produced automatically during ``agdt-review-pull-request`` scaffolding
via ``review_templates.py`` and ``status_cascade.py``.
"""

import sys


def generate_overarching_pr_comments() -> bool:  # pragma: no cover
    """
    Generate overarching review comments for each folder and overall PR summary.

    .. deprecated::
        This function is deprecated. PR summaries are now generated automatically
        during agdt-review-pull-request scaffolding. The entry point
        (agdt-generate-pr-summary) has been removed.

    Returns:
        False (always) — this function is deprecated and no longer functional.
    """
    print(
        "ERROR: generate_overarching_pr_comments() is deprecated. "
        "PR summaries are now generated automatically during "
        "agdt-review-pull-request scaffolding.",
        file=sys.stderr,
    )
    return False


def generate_overarching_pr_comments_cli() -> None:
    """
    CLI entry point for generate_overarching_pr_comments.

    .. deprecated::
        This command is deprecated. PR summaries are now generated automatically
        during agdt-review-pull-request scaffolding. The entry point
        (agdt-generate-pr-summary) has been removed.
    """
    generate_overarching_pr_comments()
