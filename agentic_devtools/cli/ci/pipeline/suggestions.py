"""GraphQL suggestion query/mutation logic, bisection fallback, and result types.

Provides the core functions for querying applicable suggestions on a PR
and applying them via the ``createCommitOnBranch`` GraphQL mutation.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field

from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.ci.retry import RetryableError

logger = logging.getLogger(__name__)

# Maximum bisection recursion depth to cap API calls
_MAX_BISECTION_DEPTH = 4
_SUGGESTION_BLOCK_PATTERN = re.compile(r"(?m)^[ \t]*```suggestion(?::-?\d+(?:\+\d+)?)?(?:[ \t].*)?\r?$")
_SUGGESTION_CONTENT_PATTERN = re.compile(
    r"```suggestion(?::-?\d+(?:\+\d+)?)?(?:[ \t].*)?(?:\r?\n)(.*?)```",
    re.DOTALL,
)


@dataclass
class SuggestedChange:
    """A single autofixable code suggestion from a review comment.

    Attributes:
        suggestion_id: GraphQL node ID of the review comment carrying the
            suggestion (used for tracking and exclusion context).
        outdated: Whether the parent review thread is outdated (stale).
        comment_database_id: REST API ``databaseId`` of the parent
            ``PullRequestReviewComment``.
        thread_id: GraphQL node ID of the parent review thread.
        path: File path the suggestion applies to.
        start_line: Start line of the range to replace (inclusive).
            Same as ``end_line`` for single-line suggestions.
        end_line: End line of the range to replace (inclusive).
        replacement: The replacement text content from the suggestion block.
    """

    suggestion_id: str
    outdated: bool
    comment_database_id: int
    thread_id: str
    path: str = ""
    start_line: int = 0
    end_line: int = 0
    replacement: str = ""


@dataclass
class ApplySuggestionsResult:
    """Structured output for batch and bisection apply flows.

    Attributes:
        applied_ids: Review-comment GraphQL node IDs for suggestions that
            were successfully applied.
        skipped_ids: Review-comment GraphQL node IDs that were excluded
            (outdated, conflicting, or errored).
        commit_shas: Ordered list of autofix commit SHAs produced by batch
            and/or fallback application.
        error: Optional error detail for partial failures.
    """

    applied_ids: list[str] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)
    commit_shas: list[str] = field(default_factory=list)
    error: str | None = None


# GraphQL query for fetching suggestion-candidate review comments on a PR
_SUGGESTIONS_QUERY = """\
query($owner: String!, $repoName: String!, $prNumber: Int!, $threadsCursor: String) {
  repository(owner: $owner, name: $repoName) {
    pullRequest(number: $prNumber) {
      id
      headRefName
      headRefOid
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 100) {
            pageInfo { hasNextPage endCursor }
            nodes {
              id
              databaseId
              body
              path
              line
              startLine
            }
          }
        }
      }
    }
  }
}
"""

# GraphQL query for paginating comments within a single review thread
_THREAD_COMMENTS_QUERY = """\
query($threadId: ID!, $commentsCursor: String) {
  node(id: $threadId) {
    ... on PullRequestReviewThread {
      comments(first: 100, after: $commentsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          databaseId
          body
          path
          line
          startLine
        }
      }
    }
  }
}
"""

# GraphQL mutation for creating a commit with applied suggestions
_CREATE_COMMIT_MUTATION = """\
mutation($repoWithOwner: String!, $branchName: String!, $headOid: GitObjectID!,
         $message: CommitMessage!, $fileChanges: FileChanges!) {
  createCommitOnBranch(input: {
    branch: {
      repositoryNameWithOwner: $repoWithOwner,
      branchName: $branchName
    },
    expectedHeadOid: $headOid,
    message: $message,
    fileChanges: $fileChanges
  }) {
    commit {
      oid
    }
  }
}
"""

# GraphQL query for fetching file content at a specific ref
_FILE_CONTENT_QUERY = """\
query($owner: String!, $repoName: String!, $expression: String!) {
  repository(owner: $owner, name: $repoName) {
    object(expression: $expression) {
      ... on Blob {
        text
      }
    }
  }
}
"""


def fetch_applicable_suggestions(
    provider: CIPlatformProvider,
    pr_number: int,
) -> tuple[list[SuggestedChange], str]:
    """Query GitHub GraphQL API for all applicable suggestions on a PR.

    Retrieves all review comments from unresolved review threads and treats
    comments containing markdown "```suggestion" fenced blocks as applicable
    suggestions. Extracts the replacement content, file path, and line range
    from each comment. Thread-level ``isOutdated`` is propagated onto each
    discovered suggestion and filtered out. Handles pagination for PRs with
    more than 100 review threads and for thread comment pages over 100.

    Args:
        provider: CI platform provider for API interactions.
        pr_number: Pull request number.

    Returns:
        Tuple of (list of applicable SuggestedChange objects, PR node ID).
        The PR node ID is needed for commit creation context.

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
            if _is_schema_error(error_str):
                logger.warning("Suggestion fetch GraphQL schema mismatch: %s", error_str)
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
            thread_outdated = bool(thread.get("isOutdated", False))
            comments_data = thread.get("comments") or {}
            comments: list[dict] = list(comments_data.get("nodes") or [])
            page_info = comments_data.get("pageInfo")
            if not isinstance(page_info, dict):
                page_info = {}
            comments_cursor = page_info.get("endCursor") if page_info.get("hasNextPage") else None
            while comments_cursor and thread_id:
                next_comments, next_page_info = _fetch_additional_thread_comments(provider, thread_id, comments_cursor)
                comments.extend(next_comments)
                comments_cursor = next_page_info.get("endCursor") if next_page_info.get("hasNextPage") else None

            for comment in comments:
                if not isinstance(comment, dict):
                    continue
                raw_db_id = comment.get("databaseId")
                comment_db_id = raw_db_id if isinstance(raw_db_id, int) else 0
                comment_id = comment.get("id")
                body = str(comment.get("body") or "")
                if not isinstance(comment_id, str) or not comment_id:
                    continue
                if _SUGGESTION_BLOCK_PATTERN.search(body):
                    replacement = _extract_suggestion_content(body)
                    if replacement is None:
                        logger.debug(
                            "Suggestion %s skipped: unable to extract replacement "
                            "content (likely missing closing backticks)",
                            comment_id,
                        )
                        continue
                    path = comment.get("path") or ""
                    end_line = comment.get("line") or 0
                    start_line = comment.get("startLine") or end_line
                    if not path or not end_line:
                        continue
                    suggestions.append(
                        SuggestedChange(
                            suggestion_id=comment_id,
                            outdated=thread_outdated,
                            comment_database_id=comment_db_id,
                            thread_id=thread_id,
                            path=path,
                            start_line=start_line,
                            end_line=end_line,
                            replacement=replacement,
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
    *,
    suggestions: list[SuggestedChange] | None = None,
    head_ref: str = "",
    head_oid: str = "",
) -> ApplySuggestionsResult:
    """Apply all given suggestions as a single commit via createCommitOnBranch.

    Fetches current file contents, applies each suggestion's replacement to the
    appropriate line range, and creates a commit on the PR branch.

    Args:
        provider: CI platform provider.
        pr_node_id: GraphQL node ID of the pull request (unused but kept for API compat).
        suggestion_ids: List of suggestion node IDs to apply.
        suggestions: Full SuggestedChange objects with path/line/replacement data.
        head_ref: Branch name for the commit.
        head_oid: Current HEAD OID for optimistic locking.

    Returns:
        ApplySuggestionsResult with applied IDs and commit SHA.
    """
    if not suggestion_ids:
        return ApplySuggestionsResult()

    if not suggestions or not head_ref or not head_oid:
        return ApplySuggestionsResult(
            skipped_ids=suggestion_ids,
            error="Missing required context (suggestions, head_ref, or head_oid)",
        )

    owner, repo_name = _get_repo_parts(provider)
    repo_with_owner = f"{owner}/{repo_name}"

    # Build a lookup from suggestion_id to SuggestedChange
    suggestion_map = {s.suggestion_id: s for s in suggestions}
    target_suggestions = [suggestion_map[sid] for sid in suggestion_ids if sid in suggestion_map]

    if not target_suggestions:
        return ApplySuggestionsResult(
            skipped_ids=suggestion_ids,
            error="No matching suggestion objects found for given IDs",
        )

    # Group suggestions by file path
    by_file: dict[str, list[SuggestedChange]] = {}
    for s in target_suggestions:
        by_file.setdefault(s.path, []).append(s)

    try:
        # Fetch file contents and apply suggestions
        file_additions: list[dict] = []
        applied_ids: list[str] = []
        skipped_ids: list[str] = []

        for file_path, file_suggestions in by_file.items():
            # Fetch current file content from the branch
            file_content = _fetch_file_content(provider, owner, repo_name, head_ref, file_path)
            if file_content is None:
                for s in file_suggestions:
                    skipped_ids.append(s.suggestion_id)
                logger.warning("Cannot fetch file %s at ref %s — skipping suggestions", file_path, head_ref)
                continue

            crlf_count = file_content.count("\r\n")
            lf_count = file_content.count("\n")
            line_sep = "\r\n" if crlf_count > 0 and crlf_count == lf_count else "\n"
            lines = file_content.split(line_sep)

            # Sort suggestions by start_line descending so we apply from bottom to top
            # (avoids line number shifts affecting later replacements)
            sorted_suggestions = sorted(file_suggestions, key=lambda s: s.start_line, reverse=True)

            # Check for overlapping suggestions
            occupied_ranges: list[tuple[int, int]] = []
            valid_suggestions: list[SuggestedChange] = []
            for s in sorted_suggestions:
                overlaps = any(
                    not (s.end_line < existing_start or s.start_line > existing_end)
                    for existing_start, existing_end in occupied_ranges
                )
                if overlaps:
                    skipped_ids.append(s.suggestion_id)
                    logger.info("Suggestion %s overlaps with another — skipping", s.suggestion_id)
                else:
                    valid_suggestions.append(s)
                    occupied_ranges.append((s.start_line, s.end_line))

            # Apply non-overlapping suggestions (already sorted bottom-to-top)
            applied_suggestion_ids_for_file: list[str] = []
            for s in valid_suggestions:
                # Lines are 1-indexed in GitHub, convert to 0-indexed
                start_idx = s.start_line - 1
                end_idx = s.end_line  # exclusive (replace lines start_idx to end_idx-1 inclusive)
                if start_idx < 0 or end_idx > len(lines):
                    skipped_ids.append(s.suggestion_id)
                    logger.warning(
                        "Suggestion %s line range %d-%d out of bounds (file has %d lines)",
                        s.suggestion_id,
                        s.start_line,
                        s.end_line,
                        len(lines),
                    )
                    continue

                # Empty replacement means "delete selected lines"
                replacement_lines = s.replacement.splitlines() if s.replacement else []
                lines[start_idx:end_idx] = replacement_lines
                applied_ids.append(s.suggestion_id)
                applied_suggestion_ids_for_file.append(s.suggestion_id)

            if applied_suggestion_ids_for_file:
                new_content = line_sep.join(lines)
                encoded = base64.b64encode(new_content.encode("utf-8")).decode("ascii")
                file_additions.append({"path": file_path, "contents": encoded})

        if not file_additions:
            return ApplySuggestionsResult(
                applied_ids=[],
                skipped_ids=suggestion_ids,
                error="No suggestions could be applied (all skipped or file fetch failed)",
            )

        # Create the commit
        count = len(applied_ids)

        response = provider.graphql(
            query=_CREATE_COMMIT_MUTATION,
            variables={
                "repoWithOwner": repo_with_owner,
                "branchName": head_ref,
                "headOid": head_oid,
                "message": {"headline": f"Apply {count} suggestion{'s' if count != 1 else ''} from code review"},
                "fileChanges": {"additions": file_additions},
            },
        )
        data = json.loads(response) if isinstance(response, str) else response

        if data.get("errors"):
            error_messages = [e.get("message", "") for e in data["errors"]]
            error_str = "; ".join(m for m in error_messages if m) or "Unknown GraphQL error"
            if _is_conflict_error(error_str):
                return ApplySuggestionsResult(
                    skipped_ids=suggestion_ids,
                    error=f"Conflict: {error_str}",
                )
            if _is_transient_error(error_str):
                raise RetryableError(f"Transient error: {error_str}")
            return ApplySuggestionsResult(
                skipped_ids=suggestion_ids,
                error=error_str,
            )

        commit_data = (data.get("data") or {}).get("createCommitOnBranch") or {}
        commit_oid = (commit_data.get("commit") or {}).get("oid", "")
        commit_shas = [commit_oid] if commit_oid else []

        return ApplySuggestionsResult(
            applied_ids=applied_ids,
            skipped_ids=skipped_ids,
            commit_shas=commit_shas,
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
    suggestions: list[SuggestedChange] | None = None,
    head_ref: str = "",
    head_oid: str = "",
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
        suggestions: Full SuggestedChange objects with path/line/replacement data.
        head_ref: Branch name for commits.
        head_oid: Current HEAD OID for optimistic locking.
        depth: Current recursion depth (internal use).

    Returns:
        ApplySuggestionsResult aggregating all successful and skipped IDs.
    """
    if not suggestion_ids:
        return ApplySuggestionsResult()

    # Try full batch first
    result = apply_suggestions_batch(
        provider,
        pr_node_id,
        suggestion_ids,
        suggestions=suggestions,
        head_ref=head_ref,
        head_oid=head_oid,
    )

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

    # After left batch commits, we need to refresh head_oid for the right batch
    left_result = apply_suggestions_with_bisection(
        provider,
        pr_node_id,
        left_ids,
        suggestions=suggestions,
        head_ref=head_ref,
        head_oid=head_oid,
        depth=depth + 1,
    )

    # Update head_oid if left produced a commit
    updated_head_oid = head_oid
    if left_result.commit_shas:
        latest_sha = left_result.commit_shas[-1]
        if latest_sha:
            updated_head_oid = latest_sha

    right_result = apply_suggestions_with_bisection(
        provider,
        pr_node_id,
        right_ids,
        suggestions=suggestions,
        head_ref=head_ref,
        head_oid=updated_head_oid,
        depth=depth + 1,
    )

    # Merge results — preserve any error from either side
    errors = [e for e in [left_result.error, right_result.error] if e]
    return ApplySuggestionsResult(
        applied_ids=left_result.applied_ids + right_result.applied_ids,
        skipped_ids=left_result.skipped_ids + right_result.skipped_ids,
        commit_shas=left_result.commit_shas + right_result.commit_shas,
        error="; ".join(errors) if errors else None,
    )


def _extract_suggestion_content(body: str) -> str | None:
    """Extract the replacement content from a markdown suggestion block.

    Parses the first ````` ```suggestion ... ``` ````` block in the comment body
    and returns the content between the fences.

    Returns:
        The suggestion replacement text, empty string for a valid delete
        suggestion, or ``None`` if no complete block is found.
    """
    match = _SUGGESTION_CONTENT_PATTERN.search(body)
    if not match:
        return None
    return match.group(1)


def _fetch_file_content(
    provider: CIPlatformProvider,
    owner: str,
    repo_name: str,
    ref: str,
    path: str,
) -> str | None:
    """Fetch file content from the repository at a given ref.

    Uses the GraphQL ``repository.object(expression:)`` query to retrieve
    the file as a Blob.

    Returns:
        File content as a string, or None if not found.

    Raises:
        RetryableError: On rate limit or transient failures.
    """
    expression = f"{ref}:{path}"
    try:
        response = provider.graphql(
            query=_FILE_CONTENT_QUERY,
            variables={
                "owner": owner,
                "repoName": repo_name,
                "expression": expression,
            },
        )
        data = json.loads(response) if isinstance(response, str) else response
        errors = data.get("errors", [])
        if errors:
            error_messages = [e.get("message", "") for e in errors if isinstance(e, dict)]
            error_str = "; ".join(msg for msg in error_messages if msg) or "Unknown GraphQL error"
            if _is_transient_error(error_str):
                raise RetryableError(f"Transient GraphQL file-content error: {error_str}")
            return None
        obj = (data.get("data") or {}).get("repository", {}).get("object")
        if not isinstance(obj, dict):
            return None
        text = obj.get("text")
        return text if isinstance(text, str) else None
    except RetryableError:
        raise
    except Exception:
        return None


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


def _is_schema_error(error_msg: str) -> bool:
    """Classify an error message as a GraphQL schema/field mismatch."""
    lower = error_msg.lower()
    return "doesn't exist on type" in lower or "cannot query field" in lower


def _fetch_additional_thread_comments(
    provider: CIPlatformProvider,
    thread_id: str,
    cursor: str,
) -> tuple[list[dict], dict]:
    """Fetch one additional paginated page of review-thread comments."""
    response = provider.graphql(
        query=_THREAD_COMMENTS_QUERY,
        variables={
            "threadId": thread_id,
            "commentsCursor": cursor,
        },
    )
    data = json.loads(response) if isinstance(response, str) else response
    errors = data.get("errors", [])
    if errors:
        error_messages = [e.get("message", "") for e in errors if isinstance(e, dict)]
        error_str = "; ".join(msg for msg in error_messages if msg) or "Unknown GraphQL error"
        if _is_transient_error(error_str):
            raise RetryableError(f"Transient GraphQL query error: {error_str}")
        if _is_schema_error(error_str):
            logger.warning("Thread comments GraphQL schema mismatch: %s", error_str)
        raise RuntimeError(f"GraphQL query failed: {error_str}")

    comments_data = (data.get("data", {}).get("node") or {}).get("comments")
    if not isinstance(comments_data, dict):
        return [], {}
    page_info = comments_data.get("pageInfo")
    if not isinstance(page_info, dict):
        page_info = {}
    return [comment for comment in (comments_data.get("nodes") or []) if isinstance(comment, dict)], page_info


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
