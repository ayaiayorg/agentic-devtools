"""GraphQL suggestion query/mutation logic, bisection fallback, and result types.

Provides the core functions for querying applicable suggestions on a PR
and applying them via the ``applySuggestedChanges`` GraphQL mutation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.retry import RetryableError

logger = logging.getLogger(__name__)

# Maximum bisection recursion depth to cap API calls
_MAX_BISECTION_DEPTH = 4


@dataclass
class SuggestedChange:
    """A single autofixable code suggestion from a review comment.

    Attributes:
        suggestion_id: GraphQL node ID of the SuggestedChange.
        outdated: Whether the suggestion is outdated (stale).
        comment_database_id: REST API ``databaseId`` of the parent
            ``PullRequestReviewComment``.
        thread_id: GraphQL node ID of the parent review thread.
    """

    suggestion_id: str
    outdated: bool
    comment_database_id: int
    thread_id: str


@dataclass
class ApplySuggestionsResult:
    """Structured output for batch and bisection apply flows.

    Attributes:
        applied_ids: GraphQL SuggestedChange node IDs that were successfully applied.
        skipped_ids: GraphQL SuggestedChange node IDs that were excluded
            (outdated, conflicting, or errored).
        commit_shas: Ordered list of autofix commit SHAs produced by batch
            and/or fallback application.
        error: Optional error detail for partial failures.
    """

    applied_ids: list[str] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)
    commit_shas: list[str] = field(default_factory=list)
    error: str | None = None


# GraphQL query for fetching suggested changes on a PR
_SUGGESTIONS_QUERY = """\
query($owner: String!, $repoName: String!, $prNumber: Int!, $threadsCursor: String) {
  repository(owner: $owner, name: $repoName) {
    pullRequest(number: $prNumber) {
      id
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          comments(first: 100) {
            nodes {
              databaseId
              suggestedChanges(first: 100) {
                nodes {
                  id
                  outdated
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

# GraphQL mutation for applying suggested changes
_APPLY_SUGGESTIONS_MUTATION = """\
mutation($pullRequestId: ID!, $suggestedChangeIds: [ID!]!) {
  applySuggestedChanges(input: {
    pullRequestId: $pullRequestId,
    suggestedChangeIds: $suggestedChangeIds
  }) {
    pullRequest { id }
    appliedSuggestedChanges { id }
  }
}
"""


def fetch_applicable_suggestions(
    provider: CIPlatformProvider,
    pr_number: int,
) -> tuple[list[SuggestedChange], str]:
    """Query GitHub GraphQL API for all applicable suggestions on a PR.

    Retrieves all SuggestedChange nodes from unresolved review threads,
    filtering out those marked as outdated. Handles pagination for PRs
    with more than 100 review threads.

    Args:
        provider: CI platform provider for API interactions.
        pr_number: Pull request number.

    Returns:
        Tuple of (list of applicable SuggestedChange objects, PR node ID).
        The PR node ID is needed for the apply mutation.

    Raises:
        RuntimeError: On non-retryable API errors.
        RetryableError: On rate limit or transient failures.
    """
    suggestions: list[SuggestedChange] = []
    pr_node_id = ""
    cursor: str | None = None

    owner, repo_name = _get_repo_parts(provider)

    while True:
        variables: dict = {
            "owner": owner,
            "repoName": repo_name,
            "prNumber": pr_number,
        }
        if cursor is not None:
            variables["threadsCursor"] = cursor

        response = provider.graphql(
            query=_SUGGESTIONS_QUERY,
            variables=variables,
        )

        data = json.loads(response) if isinstance(response, str) else response
        errors = data.get("errors", [])
        if errors:
            error_messages = [e.get("message", "") for e in errors if isinstance(e, dict)]
            error_str = "; ".join(msg for msg in error_messages if msg) or "Unknown GraphQL error"
            if _is_transient_error(error_str):
                raise RetryableError(f"Transient GraphQL query error: {error_str}")
            raise RuntimeError(f"GraphQL query failed: {error_str}")

        pr_data = data.get("data", {}).get("repository", {}).get("pullRequest")
        if not isinstance(pr_data, dict):
            raise RuntimeError("pullRequest is null or invalid in GraphQL response")
        if not pr_node_id:
            pr_node_id = pr_data.get("id", "")

        threads_data = pr_data.get("reviewThreads") or {}
        for thread in threads_data.get("nodes") or []:
            if not isinstance(thread, dict):
                continue
            # Skip resolved threads
            if thread.get("isResolved", False):
                continue

            thread_id = thread.get("id", "")
            for comment in (thread.get("comments") or {}).get("nodes") or []:
                if not isinstance(comment, dict):
                    continue
                raw_db_id = comment.get("databaseId")
                comment_db_id = raw_db_id if isinstance(raw_db_id, int) else 0
                for sc in (comment.get("suggestedChanges") or {}).get("nodes") or []:
                    if not isinstance(sc, dict):
                        continue
                    sc_id = sc.get("id")
                    if not sc_id:
                        continue
                    suggestions.append(
                        SuggestedChange(
                            suggestion_id=sc_id,
                            outdated=sc.get("outdated", False),
                            comment_database_id=comment_db_id,
                            thread_id=thread_id,
                        )
                    )

        page_info = threads_data.get("pageInfo", {})
        if page_info.get("hasNextPage") and page_info.get("endCursor"):
            cursor = page_info["endCursor"]
        else:
            break

    # Filter out outdated suggestions
    applicable = []
    for s in suggestions:
        if s.outdated:
            logger.info(
                "Suggestion %s skipped: outdated (comment_id=%d)",
                s.suggestion_id,
                s.comment_database_id,
            )
        else:
            applicable.append(s)

    return applicable, pr_node_id


def apply_suggestions_batch(
    provider: CIPlatformProvider,
    pr_node_id: str,
    suggestion_ids: list[str],
) -> ApplySuggestionsResult:
    """Apply all given suggestions in a single GraphQL mutation.

    Produces exactly one commit when the batch succeeds.

    Args:
        provider: CI platform provider.
        pr_node_id: GraphQL node ID of the pull request.
        suggestion_ids: List of suggestion node IDs to apply.

    Returns:
        ApplySuggestionsResult with applied IDs and commit SHA.
    """
    if not suggestion_ids:
        return ApplySuggestionsResult()

    try:
        response = provider.graphql(
            query=_APPLY_SUGGESTIONS_MUTATION,
            variables={
                "pullRequestId": pr_node_id,
                "suggestedChangeIds": suggestion_ids,
            },
        )
        data = json.loads(response) if isinstance(response, str) else response

        # Check for errors in the response (only when the list is non-empty)
        if data.get("errors"):
            error_messages = [e.get("message", "") for e in data["errors"]]
            error_str = "; ".join(m for m in error_messages if m) or "Unknown GraphQL error"
            # Classify as conflict if it mentions conflict-related terms
            if _is_conflict_error(error_str):
                return ApplySuggestionsResult(
                    skipped_ids=suggestion_ids,
                    error=f"Conflict: {error_str}",
                )
            # Transient errors
            if _is_transient_error(error_str):
                raise RetryableError(f"Transient error: {error_str}")
            # Fatal/unknown error
            return ApplySuggestionsResult(
                skipped_ids=suggestion_ids,
                error=error_str,
            )

        # Extract applied suggestion IDs
        mutation_data = data.get("data", {}).get("applySuggestedChanges", {})
        applied = [sc["id"] for sc in mutation_data.get("appliedSuggestedChanges", [])]

        if not applied:
            # Mutation succeeded but applied nothing (e.g. already applied, rejected, or
            # GitHub returned an empty appliedSuggestedChanges list).  Treat as skipped so
            # the repair path is not short-circuited on a false positive.
            return ApplySuggestionsResult(
                skipped_ids=suggestion_ids,
                error="Mutation returned no applied suggestions",
            )

        # The mutation produces a commit; get the SHA from the PR HEAD
        # (we'll capture it in the action via snapshot refresh)
        return ApplySuggestionsResult(
            applied_ids=applied,
            commit_shas=["pending_refresh"],  # Placeholder; actual SHA from snapshot refresh
        )

    except RetryableError:
        raise
    except Exception as exc:
        return ApplySuggestionsResult(
            skipped_ids=suggestion_ids,
            error=str(exc),
        )


def apply_suggestions_with_bisection(
    provider: CIPlatformProvider,
    pr_node_id: str,
    suggestion_ids: list[str],
    *,
    depth: int = 0,
) -> ApplySuggestionsResult:
    """Apply suggestions using bisection fallback on conflict errors.

    When the full batch fails due to conflicting hunks, subdivides the
    suggestion set and retries each half recursively. Caps recursion at
    ``_MAX_BISECTION_DEPTH`` to limit API calls.

    Args:
        provider: CI platform provider.
        pr_node_id: GraphQL node ID of the pull request.
        suggestion_ids: List of suggestion node IDs to apply.
        depth: Current recursion depth (internal use).

    Returns:
        ApplySuggestionsResult aggregating all successful and skipped IDs.
    """
    if not suggestion_ids:
        return ApplySuggestionsResult()

    # Try full batch first
    result = apply_suggestions_batch(provider, pr_node_id, suggestion_ids)

    # If no conflict error, return as-is (success or fatal error)
    if result.error is None or not _is_conflict_error(result.error):
        return result

    # Conflict: attempt bisection
    if depth >= _MAX_BISECTION_DEPTH:
        logger.warning(
            "Bisection depth %d reached with %d suggestions remaining — giving up",
            depth,
            len(suggestion_ids),
        )
        return ApplySuggestionsResult(
            skipped_ids=suggestion_ids,
            error=f"Bisection depth exceeded ({depth})",
        )

    if len(suggestion_ids) == 1:
        # Single suggestion conflicts — skip it
        logger.info("Single suggestion %s conflicts — skipping", suggestion_ids[0])
        return ApplySuggestionsResult(
            skipped_ids=suggestion_ids,
            error="Single suggestion conflict",
        )

    # Split and recurse
    mid = len(suggestion_ids) // 2
    left_ids = suggestion_ids[:mid]
    right_ids = suggestion_ids[mid:]

    logger.info(
        "Bisecting %d suggestions at depth %d: left=%d, right=%d",
        len(suggestion_ids),
        depth,
        len(left_ids),
        len(right_ids),
    )

    left_result = apply_suggestions_with_bisection(provider, pr_node_id, left_ids, depth=depth + 1)
    right_result = apply_suggestions_with_bisection(provider, pr_node_id, right_ids, depth=depth + 1)

    # Merge results — preserve any error from either side
    errors = [e for e in [left_result.error, right_result.error] if e]
    return ApplySuggestionsResult(
        applied_ids=left_result.applied_ids + right_result.applied_ids,
        skipped_ids=left_result.skipped_ids + right_result.skipped_ids,
        commit_shas=left_result.commit_shas + right_result.commit_shas,
        error="; ".join(errors) if errors else None,
    )


def _is_conflict_error(error_msg: str) -> bool:
    """Classify an error message as a conflict (overlapping hunks)."""
    conflict_indicators = [
        "conflict",
        "overlapping",
        "cannot be applied",
        "could not apply",
        "stale",
    ]
    lower = error_msg.lower()
    return any(indicator in lower for indicator in conflict_indicators)


def _is_transient_error(error_msg: str) -> bool:
    """Classify an error message as transient (retryable)."""
    transient_indicators = [
        "internal server error",
        "502",
        "503",
        "504",
        "timeout",
        "temporarily unavailable",
        "rate limit",
    ]
    lower = error_msg.lower()
    return any(indicator in lower for indicator in transient_indicators)


def _get_repo_parts(provider: CIPlatformProvider) -> tuple[str, str]:
    """Extract owner and repo name from the provider.

    Falls back to environment variable GITHUB_REPOSITORY if the provider
    doesn't expose the repo directly.
    """
    import os

    repo_str = getattr(provider, "_repo", "") or os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo_str:
        parts = repo_str.split("/", 1)
        return parts[0], parts[1]
    raise RuntimeError("Cannot determine repository owner/name. Set GITHUB_REPOSITORY or configure provider.")
