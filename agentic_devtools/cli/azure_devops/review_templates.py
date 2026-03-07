"""Markdown template engine for PR review summaries.

Provides functions to generate and regenerate full markdown content for
file summaries and the overall PR summary at each status.
"""

from typing import Dict, List, Optional

from .review_attribution import format_status, render_attribution_line
from .review_state import (
    ConsolidationStatus,
    FileEntry,
    ModelVerdict,
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


# Verdict display string mapping: per-model status → markdown display
_VERDICT_DISPLAY: Dict[str, str] = {
    ReviewStatus.UNREVIEWED.value: "⏳ Awaiting Review",
    ReviewStatus.IN_PROGRESS.value: "🔃 In Progress",
    ReviewStatus.APPROVED.value: "✅ Approved",
    ReviewStatus.NEEDS_WORK.value: "📝 Needs Work",
}


def render_model_review_progress_table(
    model_verdicts: List[ModelVerdict],
    consolidation_status: Optional[str] = None,
    boss_model: Optional[str] = None,
    final_verdict: Optional[str] = None,
) -> str:
    """Render the Model Review Progress table in markdown.

    Intended to be present in file review comments for both single-model and
    multi-model reviews.  Returns an empty string when ``model_verdicts`` is
    empty so callers can safely concatenate the result.

    The consolidator does not appear as a row — it appears as an attribution
    note below the table only when consolidation runs.

    Args:
        model_verdicts: Per-model verdict entries for this file.  When empty,
            the function returns ``""`` (no table rendered).
        consolidation_status: Consolidation status for this file (from
            ``ConsolidationStatus``), or ``None`` if not applicable.
        boss_model: Boss/consolidator model name. Used in the consolidation
            attribution note when consolidation runs.
        final_verdict: Display string for the final consolidated verdict
            (e.g. "✅ Approved" or "📝 Needs Work").  When ``None`` and
            ``consolidation_status`` is ``COMPLETE``, defaults to
            "✅ Approved".

    Returns:
        Markdown string containing the table (including the ``###`` header),
        or an empty string if ``model_verdicts`` is empty.
    """
    if not model_verdicts:
        return ""

    lines: List[str] = [
        "### Model Review Progress",
        "",
        "| Model | Verdict |",
        "|---|---|",
    ]

    for mv in model_verdicts:
        verdict_display = _VERDICT_DISPLAY.get(mv.status, mv.status)
        lines.append(f"| {mv.modelId} | {verdict_display} |")

    # Consolidation attribution note (below the table)
    if consolidation_status == ConsolidationStatus.IN_PROGRESS and boss_model:
        lines.append("")
        lines.append(f"*🔃 Consolidation underway by {boss_model}*")
    elif consolidation_status == ConsolidationStatus.COMPLETE and boss_model:
        resolved_verdict = final_verdict if final_verdict else "✅ Approved"
        lines.append("")
        lines.append(f"*Consolidated by {boss_model} — Final verdict: {resolved_verdict}*")

    return "\n".join(lines)


def render_file_summary(
    file_entry: FileEntry,
    suggestions: List[SuggestionEntry],
    base_url: str,
    model_name: Optional[str] = None,
    model_icon: Optional[str] = None,
    commit_hash: Optional[str] = None,
    commit_url: Optional[str] = None,
    boss_model: Optional[str] = None,
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
        boss_model: Boss/consolidator model name. Passed through to
            ``render_model_review_progress_table()`` for consolidation attribution.

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

    # Model Review Progress table (always attempt to render; returns empty for no verdicts)
    progress_table = render_model_review_progress_table(
        file_entry.modelVerdicts or [],
        consolidation_status=file_entry.consolidationStatus,
        boss_model=boss_model,
    )
    if progress_table:
        lines += ["", progress_table]

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

    known_statuses = set(status_folder_files.keys())
    for fe in state.files.values():
        # Normalize unknown statuses into the unreviewed bucket so every
        # file appears in a rendered section.
        status = fe.status if fe.status in known_statuses else ReviewStatus.UNREVIEWED.value
        folder = fe.folder if fe.folder else "root"
        status_folder_files[status].setdefault(folder, []).append(fe)

    # Overall status derived from file statuses, with the same unknown→unreviewed
    # normalization so the header status matches the rendered sections.
    file_statuses_all = [
        f.status if f.status in known_statuses else ReviewStatus.UNREVIEWED.value for f in state.files.values()
    ]
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
        (ReviewStatus.APPROVED.value, "✅ Approved"),
        (ReviewStatus.IN_PROGRESS.value, "🔃 In Progress"),
        (ReviewStatus.UNREVIEWED.value, "⏳ Unreviewed"),
    ]

    for status_val, section_title in sections:
        folder_files = status_folder_files.get(status_val, {})
        if not folder_files:
            continue
        lines.extend(["", f"### {section_title}"])
        for folder_name in sorted(folder_files.keys()):
            lines.append(f"- {folder_name}")
            for fe in sorted(folder_files[folder_name], key=_file_display_path):
                # Use the section status for emoji so unknown statuses
                # normalized into Unreviewed still get the ⏳ prefix.
                file_emoji = _STATUS_EMOJI.get(status_val, "")
                url = build_discussion_url(base_url, fe.threadId, fe.commentId)
                display = _file_display_path(fe)
                item = f"   - {file_emoji} [{display}]({url})"
                if status_val == ReviewStatus.NEEDS_WORK.value:
                    counts = _format_severity_counts(fe.suggestions)
                    if counts:
                        item += f" \u2014 {counts}"
                lines.append(item)

    # Review Narrative section
    lines.extend(["", "### Review Narrative", ""])
    narrative = state.overallSummary.narrativeSummary
    lines.append(narrative if narrative else "Awaiting review...")

    return "\n".join(lines)
