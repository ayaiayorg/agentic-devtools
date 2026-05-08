"""Convergence verification — re-fetch from API and confirm state."""

from __future__ import annotations

from typing import Any

from ..config import AzureDevOpsConfig
from .convergence import normalize_for_comparison
from .models import ConvergenceResult, EligibleComment, EligibleComments


def verify_convergence(
    eligible: EligibleComments,
    expected_map: dict[int, str],
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    pr_id: int,
    repo_id: str,
) -> list[ConvergenceResult]:
    """Verify convergence by re-fetching comments from the API.

    Re-reads individual comments via GET (not cache) and compares against
    expected terminal content.

    Args:
        eligible: The classified eligible comments.
        expected_map: Map of comment_id → expected body content (marker-free).
        config: Azure DevOps configuration.
        headers: Auth headers for API calls.
        pr_id: Pull request ID.
        repo_id: Repository ID for API URL construction.

    Returns:
        List of ConvergenceResult for each checked comment.
    """
    results: list[ConvergenceResult] = []
    all_comments = _collect_all_comments(eligible)

    for comment in all_comments:
        expected = expected_map.get(comment.comment_id, "")
        try:
            current_content = _fetch_comment_content(config, headers, repo_id, pr_id, comment)
            observed = normalize_for_comparison(current_content)
            converged = observed.strip() == expected.strip()
            results.append(
                ConvergenceResult(
                    comment=comment,
                    converged=converged,
                    expected_content=expected,
                    observed_content=current_content,
                )
            )
        except Exception:
            results.append(
                ConvergenceResult(
                    comment=comment,
                    converged=False,
                    expected_content=expected,
                    observed_content=comment.current_content,
                )
            )

    return results


def _collect_all_comments(eligible: EligibleComments) -> list[EligibleComment]:
    """Collect all eligible comments into a flat list."""
    comments: list[EligibleComment] = list(eligible.file_summaries)
    if eligible.overall_summary is not None:
        comments.append(eligible.overall_summary)
    comments.extend(eligible.activity_log_entries)
    return comments


def _fetch_comment_content(
    config: AzureDevOpsConfig,
    headers: dict[str, str],
    repo_id: str,
    pr_id: int,
    comment: EligibleComment,
) -> str:
    """Fetch a single comment's current content from the API."""
    from ..helpers import require_requests

    requests_module: Any = require_requests()
    url = config.build_api_url(
        repo_id,
        "pullRequests",
        pr_id,
        "threads",
        comment.thread_id,
        "comments",
        comment.comment_id,
    )
    response = requests_module.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("content", "")
