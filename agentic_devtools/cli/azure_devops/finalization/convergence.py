"""Convergence computation — expected content rendering and comparison."""

from __future__ import annotations

from ..marker import parse_marker
from ..review_state import COMPLETE_STATUSES, ReviewState, ReviewStatus
from ..review_templates import render_file_summary, render_overall_summary
from .models import EligibleComment


def strip_marker_line(content: str) -> str:
    """Strip the leading AGDT marker line from content.

    Uses ``parse_marker()`` internally to detect the marker.  If a marker
    is found, removes the first line (which contains the marker) from
    the content.  If no marker is present, returns content unchanged.

    Args:
        content: Arbitrary content string that may start with a marker line.

    Returns:
        Content with the leading marker line removed, or unchanged if no
        marker is present.
    """
    if not content:
        return content

    parsed = parse_marker(content)
    if parsed is None:
        return content

    # The marker is on the first line — remove it
    lines = content.split("\n", 1)
    if len(lines) > 1:
        return lines[1]
    return ""


def compute_expected_content(
    comment: EligibleComment,
    review_state: ReviewState,
    base_url: str,
) -> str:
    """Compute the expected terminal content for an eligible comment.

    Dispatches to the appropriate renderer based on marker type and returns
    **body-only content without the leading marker line**.

    Args:
        comment: The eligible comment to compute expected content for.
        review_state: Current review state (source of truth).
        base_url: PR root URL for building discussion links.

    Returns:
        Expected body content (marker-free) for the comment.
    """
    if comment.marker_type == "file-summary":
        return _compute_file_summary_content(comment, review_state, base_url)
    elif comment.marker_type == "overall-summary":
        return _compute_overall_summary_content(review_state, base_url)
    elif comment.marker_type == "activity-log-entry":
        return _compute_activity_log_content(review_state)
    return ""


def normalize_for_comparison(content: str) -> str:
    """Normalize content for convergence comparison.

    Strips the leading marker line (if present) so both observed and
    expected content can be compared on a marker-free basis.

    Args:
        content: Content string (may contain a leading marker line).

    Returns:
        Content with the leading marker line stripped.
    """
    return strip_marker_line(content)


def check_convergence(comment: EligibleComment, expected: str) -> bool:
    """Check if a comment's observed content matches the expected terminal content.

    Normalizes the observed content (strips marker line) before comparison.

    Args:
        comment: The eligible comment with current observed content.
        expected: Expected body content (already marker-free from
            ``compute_expected_content()``).

    Returns:
        True if the comment has converged (content matches), False otherwise.
    """
    observed = normalize_for_comparison(comment.current_content)
    return observed.strip() == expected.strip()


def _compute_file_summary_content(
    comment: EligibleComment,
    review_state: ReviewState,
    base_url: str,
) -> str:
    """Compute expected file summary content."""
    file_path = comment.file_path
    if not file_path or file_path not in review_state.files:
        return ""

    file_entry = review_state.files[file_path]
    # Ensure file has a terminal status
    if file_entry.status not in COMPLETE_STATUSES:
        file_entry.status = ReviewStatus.APPROVED.value

    suggestions = file_entry.suggestions or []
    rendered = render_file_summary(file_entry, suggestions, base_url)
    return rendered


def _compute_overall_summary_content(
    review_state: ReviewState,
    base_url: str,
) -> str:
    """Compute expected overall summary content."""
    rendered = render_overall_summary(review_state, base_url)
    return rendered


def _compute_activity_log_content(review_state: ReviewState) -> str:
    """Compute expected activity log entry content for the completed session.

    Returns the body portion only (no marker line) of a completed session
    activity log entry.
    """
    from ..review_scaffold import _format_activity_log_entry

    if not review_state.sessions:
        return ""

    session = review_state.sessions[-1]
    commit_hash = review_state.commitHash or "unknown"
    short_hash = commit_hash[:7]
    session_index = len(review_state.sessions)

    entry = _format_activity_log_entry(
        status_emoji="✅",
        status_text="Completed",
        timestamp=session.completedUtc or session.startedUtc,
        model_name=session.modelId,
        short_hash=short_hash,
        session_id=session.sessionId,
        detail_message="Review session completed successfully.",
        sequence_number=session_index,
    )
    # Strip the marker line that _format_activity_log_entry prepends
    return strip_marker_line(entry)
