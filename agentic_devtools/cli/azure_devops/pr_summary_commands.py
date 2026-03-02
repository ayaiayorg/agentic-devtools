"""
Pull Request Summary Commands.

Generates overarching PR review comments after all files have been reviewed.
This mirrors the generate-overarching-pr-comments.ps1 functionality.

.. deprecated::
    This module is deprecated. PR summaries are now generated automatically
    during agdt-review-pull-request scaffolding. The legacy helper functions
    and the ``_build_folder_comment`` flow have been removed.
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
