"""Markdown template engine for PR review summaries.

Provides functions to generate and regenerate full markdown content for
file summaries, folder summaries, and the overall PR summary at each status.
"""

from typing import Dict, List

from .review_state import FileEntry, FolderEntry, ReviewState, ReviewStatus, SuggestionEntry

_STATUS_DISPLAY: Dict[str, str] = {
    ReviewStatus.UNREVIEWED.value: "Unreviewed",
    ReviewStatus.IN_PROGRESS.value: "In Progress",
    ReviewStatus.APPROVED.value: "Approved",
    ReviewStatus.NEEDS_WORK.value: "Needs Work",
}

_SEVERITY_LABELS: Dict[str, str] = {
    "high": "Must Fix (High)",
    "medium": "Should Fix (Medium)",
    "low": "Could Fix (Low)",
}

_SEVERITY_ORDER: List[str] = ["high", "medium", "low"]


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


def render_file_summary(file_entry: FileEntry, suggestions: List[SuggestionEntry], base_url: str) -> str:
    """Render a file review summary in markdown format.

    Args:
        file_entry: FileEntry dataclass with file metadata and review status.
        suggestions: List of suggestions to render (used for needs-work status).
        base_url: PR root URL for building discussion links.

    Returns:
        Markdown string for the file review summary.
    """
    complete_path = _file_display_path(file_entry)
    status = file_entry.status
    status_display = _STATUS_DISPLAY.get(status, status)

    lines: List[str] = [
        f"## File Review Summary: {file_entry.fileName}",
        "",
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


def render_folder_summary(
    folder_name: str,
    folder_entry: FolderEntry,
    files: Dict[str, FileEntry],
    base_url: str,
) -> str:
    """Render a folder review summary in markdown format.

    Args:
        folder_name: Display name for the folder.
        folder_entry: FolderEntry containing file paths and thread metadata.
        files: Mapping of file paths to FileEntry objects (from ReviewState.files).
        base_url: PR root URL for building discussion links.

    Returns:
        Markdown string for the folder review summary.
    """
    needs_work: List[FileEntry] = []
    approved: List[FileEntry] = []
    in_progress: List[FileEntry] = []
    unreviewed: List[FileEntry] = []

    for file_path in folder_entry.files:
        fe = files.get(file_path)
        if fe is None:
            continue
        if fe.status == ReviewStatus.NEEDS_WORK.value:
            needs_work.append(fe)
        elif fe.status == ReviewStatus.APPROVED.value:
            approved.append(fe)
        elif fe.status == ReviewStatus.IN_PROGRESS.value:
            in_progress.append(fe)
        else:
            unreviewed.append(fe)

    if needs_work:
        folder_status = "Needs Work"
    elif in_progress:
        folder_status = "In Progress"
    elif approved:
        folder_status = "Approved"
    else:
        folder_status = "Unreviewed"

    lines: List[str] = [
        f"## Folder Review Summary: {folder_name}",
        "",
        f"*Status:* {folder_status}",
    ]

    def _append_file_section(title: str, entries: List[FileEntry], show_severity: bool) -> None:
        lines.extend(["", f"### {title}"])
        for fe in entries:
            url = build_discussion_url(base_url, fe.threadId, fe.commentId)
            display = _file_display_path(fe)
            item = f"[{display}]({url})"
            if show_severity:
                counts = _format_severity_counts(fe.suggestions)
                if counts:
                    item += f" \u2014 {counts}"
            lines.append(f"- {item}")

    if needs_work:
        _append_file_section("Needs Work", needs_work, show_severity=True)
    if approved:
        _append_file_section("Approved", approved, show_severity=False)
    if in_progress:
        _append_file_section("In Progress", in_progress, show_severity=False)
    if unreviewed:
        _append_file_section("Unreviewed", unreviewed, show_severity=False)

    return "\n".join(lines)


def render_overall_summary(state: ReviewState, base_url: str) -> str:
    """Render the overall PR review summary in markdown format.

    Args:
        state: Full ReviewState containing all folders and files.
        base_url: PR root URL for building discussion links.

    Returns:
        Markdown string for the overall PR review summary.
    """
    needs_work: List[str] = []
    approved: List[str] = []
    in_progress: List[str] = []
    unreviewed: List[str] = []

    for folder_name, folder_entry in state.folders.items():
        if folder_entry.status == ReviewStatus.NEEDS_WORK.value:
            needs_work.append(folder_name)
        elif folder_entry.status == ReviewStatus.APPROVED.value:
            approved.append(folder_name)
        elif folder_entry.status == ReviewStatus.IN_PROGRESS.value:
            in_progress.append(folder_name)
        else:
            unreviewed.append(folder_name)

    if needs_work:
        overall_status = "Needs Work"
    elif in_progress:
        overall_status = "In Progress"
    elif approved:
        overall_status = "Approved"
    else:
        overall_status = "Unreviewed"

    lines: List[str] = [
        "## Overall PR Review Summary",
        "",
        f"*Status:* {overall_status}",
    ]

    def _append_folder_section(title: str, folder_names: List[str]) -> None:
        lines.extend(["", f"### {title}"])
        for fn in folder_names:
            fe = state.folders[fn]
            url = build_discussion_url(base_url, fe.threadId, fe.commentId)
            lines.append(f"- [{fn}]({url})")

    if needs_work:
        _append_folder_section("Needs Work", needs_work)
    if approved:
        _append_folder_section("Approved", approved)
    if in_progress:
        _append_folder_section("In Progress", in_progress)
    if unreviewed:
        _append_folder_section("Unreviewed", unreviewed)

    return "\n".join(lines)
