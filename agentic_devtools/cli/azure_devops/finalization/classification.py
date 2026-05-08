"""Comment classification for finalization — marker-based + authorship filtering."""

from __future__ import annotations

from ..marker import classify_agdt_threads, parse_marker
from ..review_state import ReviewState
from .models import EligibleComment, EligibleComments


def classify_eligible_comments(
    threads: list[dict],
    pat_user_id: str,
    review_state: ReviewState,
) -> EligibleComments:
    """Classify PR threads into eligible AGDT comments for finalization.

    Uses ``classify_agdt_threads()`` for marker-based grouping, then filters
    by authorship (``author.id == pat_user_id``).  Comments authored by a
    different user are added to the ``skipped`` list with a reason.

    Activity-log-entry comments are found by scanning *replies* within
    activity-log threads (since ``classify_agdt_threads()`` only inspects
    the first comment).  Only the entry matching the latest session ID
    from ``review_state`` is included.

    Args:
        threads: List of Azure DevOps thread dicts (full API response).
        pat_user_id: The current PAT user's GUID for authorship checks.
        review_state: Current review state for session scoping.

    Returns:
        EligibleComments with classified file-summaries, overall-summary,
        activity-log-entries, and skipped items.
    """
    result = EligibleComments()
    classified = classify_agdt_threads(threads)

    # Process file-summary threads
    for thread in classified.get("file-summary", []):
        _process_thread_first_comment(thread, pat_user_id, "file-summary", result)

    # Process overall-summary threads
    for thread in classified.get("overall-summary", []):
        comment = _extract_first_comment(thread, pat_user_id, "overall-summary", result)
        if comment is not None:
            result.overall_summary = comment

    # Process activity-log threads — scan replies for activity-log-entry markers
    latest_session_id = None
    if review_state.sessions:
        latest_session_id = review_state.sessions[-1].sessionId

    for thread in classified.get("activity-log", []):
        _scan_activity_log_replies(thread, pat_user_id, latest_session_id, result)

    return result


def _process_thread_first_comment(
    thread: dict,
    pat_user_id: str,
    marker_type: str,
    result: EligibleComments,
) -> None:
    """Process the first comment of a thread for file-summary type."""
    comment = _extract_first_comment(thread, pat_user_id, marker_type, result)
    if comment is not None:
        result.file_summaries.append(comment)


def _extract_first_comment(
    thread: dict,
    pat_user_id: str,
    marker_type: str,
    result: EligibleComments,
) -> EligibleComment | None:
    """Extract an EligibleComment from the first comment of a thread.

    Returns None and adds a skip entry if the comment is not authored
    by the current PAT user.
    """
    comments = thread.get("comments", [])
    if not comments:
        return None

    first = comments[0]
    content = first.get("content", "")
    author_id = _get_author_id(first)

    if author_id != pat_user_id:
        result.skipped.append(
            {
                "thread_id": str(thread.get("id", "")),
                "reason": f"not editable by current user (authored by {author_id})",
            }
        )
        return None

    parsed = parse_marker(content)
    file_path = parsed.get("file") if parsed else None

    return EligibleComment(
        thread_id=thread.get("id", 0),
        comment_id=first.get("id", 0),
        marker_type=marker_type,
        marker_data=parsed or {},
        current_content=content,
        file_path=file_path,
    )


def _scan_activity_log_replies(
    thread: dict,
    pat_user_id: str,
    latest_session_id: str | None,
    result: EligibleComments,
) -> None:
    """Scan replies within an activity-log thread for activity-log-entry markers.

    Only includes entries that match the latest session ID from review state.
    """
    comments = thread.get("comments", [])
    thread_id = thread.get("id", 0)

    for comment in comments:
        content = comment.get("content", "")
        parsed = parse_marker(content)
        if parsed is None:
            continue
        if parsed.get("type") != "activity-log-entry":
            continue

        author_id = _get_author_id(comment)
        if author_id != pat_user_id:
            result.skipped.append(
                {
                    "thread_id": str(thread_id),
                    "comment_id": str(comment.get("id", "")),
                    "reason": f"not editable by current user (authored by {author_id})",
                }
            )
            continue

        # Session scoping: if we have a latest session ID, check if this entry
        # contains it (session ID is embedded in the content)
        if latest_session_id and latest_session_id not in content:
            continue

        result.activity_log_entries.append(
            EligibleComment(
                thread_id=thread_id,
                comment_id=comment.get("id", 0),
                marker_type="activity-log-entry",
                marker_data=parsed,
                current_content=content,
            )
        )


def _get_author_id(comment: dict) -> str | None:
    """Extract the author ID from a comment dict."""
    author = comment.get("author", {})
    return author.get("id")
