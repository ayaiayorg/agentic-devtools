"""Markdown template engine for PR review summaries.

Provides functions to generate and regenerate full markdown content for
file summaries and the overall PR summary at each status.
"""

from typing import Dict, List, Optional

from .review_attribution import format_status, render_attribution_line
from .review_state import (
    FileEntry,
    ReviewState,
    ReviewStatus,
    SuggestionEntry,
    compute_aggregate_status,
)

_SEVERITY_LABELS: Dict[str, str] = {
    "high": "Must Fix (High)",
    "medium": "Should Fix (Medium)",
    "low": "Could Fix (Low)",
}

_SEVERITY_ORDER: List[str] = ["high", "medium", "low"]

# Emoji character for each file/folder status (used in nested file lists)
_STATUS_EMOJI: Dict[str, str] = {
    ReviewStatus.NEEDS_WORK.value: "📝",
    ReviewStatus.APPROVED.value: "✅",
    ReviewStatus.IN_PROGRESS.value: "🔃",
    ReviewStatus.UNREVIEWED.value: "⏳",
}


def build_discussion_url(base_url: str, thread_id: int, comment_id: int) -> str:
    """Build a discussion URL for a PR thread comment.

    Args:
        base_url: PR root URL (e.g. https://dev.azure.com/org/project/_git/repo/pullRequest/123)
        thread_id: Thread ID.
        comment_id: Comment ID.

    Returns:
        Full URL with discussionId and commentId query parameters.
    """
    return f"{base_url}?discussionId={thread_id}&commentId={comment_id}"


def _file_display_path(file_entry: FileEntry) -> str:
    """Get the display path for a file entry (e.g. /src/app.py)."""
    folder = file_entry.folder
    if not folder or folder.lower() == "root":
        return f"/{file_entry.fileName}"
    return f"/{folder}/{file_entry.fileName}"


def _format_severity_counts(suggestions: List[SuggestionEntry]) -> str:
    """Format severity counts as a human-readable string (e.g. '2 High, 1 Medium')."""
    counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for s in suggestions:
        sev = s.severity.lower()
        if sev in counts:
            counts[sev] += 1
    parts = [f"{counts[sev]} {sev.capitalize()}" for sev in _SEVERITY_ORDER if counts[sev] > 0]
    return ", ".join(parts)


def render_file_summary(
    file_entry: FileEntry,
    suggestions: List[SuggestionEntry],
    base_url: str,
    model_name: Optional[str] = None,
    model_icon: Optional[str] = None,
    commit_hash: Optional[str] = None,
    commit_url: Optional[str] = None,
) -> str:
    """Render a file review summary in markdown format.

    Args:
        file_entry: FileEntry dataclass with file metadata and review status.
        suggestions: List of suggestions to render (used for needs-work status).
        base_url: PR root URL for building discussion links.
        model_name: AI model identifier (e.g. "Claude Opus 4.6"). When provided
            together with ``commit_hash``, an attribution line is prepended.
        model_icon: Override for the model family icon. Auto-detected when None.
        commit_hash: Commit hash reviewed. When provided together with
            ``model_name``, an attribution line is prepended.
        commit_url: URL to the file at the reviewed commit. Used in the
            attribution line link.

    Returns:
        Markdown string for the file review summary.
    """
    complete_path = _file_display_path(file_entry)
    status = file_entry.status
    status_display = format_status(status, use_emoji=True)

    lines: List[str] = [
        f"## File Review Summary: {file_entry.fileName}",
        "",
    ]

    attribution = render_attribution_line(model_name, model_icon, commit_hash, commit_url)
    if attribution:
        lines += [attribution, ""]

    lines += [
        f"*Complete Path:* {complete_path}",
        "",
        f"*Status:* {status_display}",
        "",
        "### Summary of Changes",
    ]

    if status == ReviewStatus.UNREVIEWED.value:
        lines.append("Awaiting review...")
        lines += ["", "### Suggestions", "Awaiting review..."]

    elif status == ReviewStatus.IN_PROGRESS.value:
        lines.append("Review in progress...")
        lines += ["", "### Suggestions", "Review in progress..."]

    elif status == ReviewStatus.APPROVED.value:
        lines.append(file_entry.summary or "")
        lines += ["", "### Suggestions", "- None"]

    elif status == ReviewStatus.NEEDS_WORK.value:
        lines.append(file_entry.summary or "")
        lines += ["", "### Suggestions"]

        by_severity: Dict[str, List[SuggestionEntry]] = {sev: [] for sev in _SEVERITY_ORDER}
        for s in suggestions:
            sev = s.severity.lower()
            if sev in by_severity:
                by_severity[sev].append(s)

        for sev in _SEVERITY_ORDER:
            group = by_severity[sev]
            if not group:
                continue
            lines += ["", f"#### {_SEVERITY_LABELS[sev]}"]
            for s in group:
                url = build_discussion_url(base_url, s.threadId, s.commentId)
                item = f"[{s.linkText}]({url})"
                if s.outOfScope:
                    item += " *(out of scope)*"
                lines.append(f"- {item}")

    return "\n".join(lines)


def render_overall_summary(
    state: ReviewState,
    base_url: str,
    model_name: Optional[str] = None,
    model_icon: Optional[str] = None,
    commit_hash: Optional[str] = None,
    commit_url: Optional[str] = None,
) -> str:
    """Render the overall PR review summary in markdown format.

    Produces a nested file list grouped by folder within each status section.
    Overall status is derived directly from file statuses. Folders are
    lightweight groupings — no folder-level threads are created or linked.

    Args:
        state: Full ReviewState containing all folders and files.
        base_url: PR root URL for building discussion links.
        model_name: AI model identifier. When provided together with
            ``commit_hash``, an attribution line is prepended.
        model_icon: Override for the model family icon. Auto-detected when None.
        commit_hash: Commit hash reviewed. When provided together with
            ``model_name``, an attribution line is prepended.
        commit_url: URL to the PR files tab at the reviewed commit. Used in the
            attribution line link.

    Returns:
        Markdown string for the overall PR review summary.
    """
    # Build per-status, per-folder file groups: status → folder → [FileEntry]
    status_folder_files: Dict[str, Dict[str, List[FileEntry]]] = {
        ReviewStatus.NEEDS_WORK.value: {},
        ReviewStatus.IN_PROGRESS.value: {},
        ReviewStatus.APPROVED.value: {},
        ReviewStatus.UNREVIEWED.value: {},
    }

    for fe in state.files.values():
        status = fe.status
        if status not in status_folder_files:
            status_folder_files[status] = {}
        folder = fe.folder if fe.folder else "root"
        status_folder_files[status].setdefault(folder, []).append(fe)

    # Overall status derived directly from file statuses
    file_statuses_all = [f.status for f in state.files.values()]
    overall_status = format_status(
        compute_aggregate_status(file_statuses_all),
        use_emoji=True,
    )

    lines: List[str] = [
        "## Overall PR Review Summary",
        "",
    ]

    attribution = render_attribution_line(model_name, model_icon, commit_hash, commit_url)
    if attribution:
        lines += [attribution, ""]

    lines.append(f"*Status:* {overall_status}")

    # Status sections in display priority order
    sections = [
        (ReviewStatus.NEEDS_WORK.value, "📝 Needs Work"),
        (ReviewStatus.IN_PROGRESS.value, "🔃 In Progress"),
        (ReviewStatus.APPROVED.value, "✅ Approved"),
        (ReviewStatus.UNREVIEWED.value, "⏳ Unreviewed"),
    ]

    for status_val, section_title in sections:
        folder_files = status_folder_files.get(status_val, {})
        if not folder_files:
            continue
        lines.extend(["", f"### {section_title}"])
        for folder_name in sorted(folder_files.keys()):
            lines.append(f"- {folder_name}")
            for fe in folder_files[folder_name]:
                file_emoji = _STATUS_EMOJI.get(fe.status, "")
                url = build_discussion_url(base_url, fe.threadId, fe.commentId)
                display = _file_display_path(fe)
                item = f"   - {file_emoji} [{display}]({url})"
                if fe.status == ReviewStatus.NEEDS_WORK.value:
                    counts = _format_severity_counts(fe.suggestions)
                    if counts:
                        item += f" \u2014 {counts}"
                lines.append(item)

    # Review Narrative section
    lines.extend(["", "### Review Narrative", ""])
    narrative = state.overallSummary.narrativeSummary
    lines.append(narrative if narrative else "Awaiting review...")

    return "\n".join(lines)
