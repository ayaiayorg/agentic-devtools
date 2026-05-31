"""Markdown template engine for PR review summaries.

Provides functions to generate and regenerate full markdown content for
file summaries and the overall PR summary at each status.
"""

import re

from .review_attribution import SHORT_HASH_LENGTH, format_status, render_attribution_line
from .review_state import (
    ConsolidationStatus,
    FileEntry,
    ModelVerdict,
    ReviewState,
    ReviewStatus,
    SuggestionEntry,
    compute_aggregate_status,
)

_SEVERITY_LABELS: dict[str, str] = {
    "high": "Must Fix (High)",
    "medium": "Should Fix (Medium)",
    "low": "Could Fix (Low)",
}

_SEVERITY_ORDER: list[str] = ["high", "medium", "low"]

# Emoji character for each file/folder status (used in nested file lists)
_STATUS_EMOJI: dict[str, str] = {
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


def _format_severity_counts(suggestions: list[SuggestionEntry]) -> str:
    """Format severity counts as a human-readable string (e.g. '2 High, 1 Medium')."""
    counts: dict[str, int] = {"high": 0, "medium": 0, "low": 0}
    for s in suggestions:
        sev = s.severity.lower()
        if sev in counts:
            counts[sev] += 1
    parts = [f"{counts[sev]} {sev.capitalize()}" for sev in _SEVERITY_ORDER if counts[sev] > 0]
    return ", ".join(parts)


# Verdict display string mapping: per-model status → markdown display
_VERDICT_DISPLAY: dict[str, str] = {
    ReviewStatus.UNREVIEWED.value: "⏳ Awaiting Review",
    ReviewStatus.IN_PROGRESS.value: "🔃 In Progress",
    ReviewStatus.APPROVED.value: "✅ Approved",
    ReviewStatus.NEEDS_WORK.value: "📝 Needs Work",
}


def render_model_review_progress_table(
    model_verdicts: list[ModelVerdict],
    consolidation_status: str | None = None,
    boss_model: str | None = None,
    final_verdict: str | None = None,
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

    lines: list[str] = [
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
    suggestions: list[SuggestionEntry],
    base_url: str,
    model_name: str | None = None,
    model_icon: str | None = None,
    commit_hash: str | None = None,
    commit_url: str | None = None,
    boss_model: str | None = None,
    is_subsequent: bool = False,
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
        is_subsequent: When True, emit a compact ``### Commit:`` header instead
            of the full ``## File Review Summary:`` title. Used for reply comments.

    Returns:
        Markdown string for the file review summary.
    """
    status = file_entry.status
    status_display = format_status(status, use_emoji=True)

    if is_subsequent:
        header = _build_subsequent_header(commit_hash, commit_url)
    else:
        header = f"## File Review Summary: {file_entry.fileName}"

    lines: list[str] = [
        header,
        "",
    ]

    attribution = render_attribution_line(model_name, model_icon, commit_hash, commit_url)
    if attribution:
        lines += [attribution, ""]

    lines += [
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

        by_severity: dict[str, list[SuggestionEntry]] = {sev: [] for sev in _SEVERITY_ORDER}
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
    model_name: str | None = None,
    model_icon: str | None = None,
    commit_hash: str | None = None,
    commit_url: str | None = None,
    is_subsequent: bool = False,
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
        is_subsequent: When True, emit a compact ``### Commit:`` header instead
            of the full ``## Overall PR Review Summary`` title. Used for reply
            comments.

    Returns:
        Markdown string for the overall PR review summary.
    """
    # Build per-status, per-folder file groups: status → folder → [(full_path, FileEntry)]
    status_folder_files: dict[str, dict[str, list[tuple[str, FileEntry]]]] = {
        ReviewStatus.NEEDS_WORK.value: {},
        ReviewStatus.IN_PROGRESS.value: {},
        ReviewStatus.APPROVED.value: {},
        ReviewStatus.UNREVIEWED.value: {},
    }

    known_statuses = set(status_folder_files.keys())
    for file_key, fe in state.files.items():
        # Normalize unknown statuses into the unreviewed bucket so every
        # file appears in a rendered section.
        status = fe.status if fe.status in known_statuses else ReviewStatus.UNREVIEWED.value
        folder = fe.folder if fe.folder else "root"
        status_folder_files[status].setdefault(folder, []).append((file_key, fe))

    # Overall status derived from file statuses, with the same unknown→unreviewed
    # normalization so the header status matches the rendered sections.
    file_statuses_all = [
        f.status if f.status in known_statuses else ReviewStatus.UNREVIEWED.value for f in state.files.values()
    ]
    overall_status = format_status(
        compute_aggregate_status(file_statuses_all),
        use_emoji=True,
    )

    if is_subsequent:
        header = _build_subsequent_header(commit_hash, commit_url)
    else:
        header = "## Overall PR Review Summary"

    lines: list[str] = [
        header,
        "",
    ]

    attribution = render_attribution_line(model_name, model_icon, commit_hash, commit_url)
    if attribution:
        lines += [attribution, ""]

    lines.append(f"*Status:* {overall_status}")

    if state.rebaseConflicts:
        _rebase_warning = (
            "> ⚠️ **Rebase Conflicts Detected** — This review was performed on code that could"
            " not be rebased onto the target branch. The reviewed code may be out of date with main."
        )
        lines.extend(["", _rebase_warning])

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
            for file_key, fe in sorted(folder_files[folder_name], key=lambda x: x[0]):
                # Use the section status for emoji so unknown statuses
                # normalized into Unreviewed still get the ⏳ prefix.
                file_emoji = _STATUS_EMOJI.get(status_val, "")
                url = build_discussion_url(base_url, fe.threadId, fe.commentId)
                item = f"   - {file_emoji} [{file_key}]({url})"
                if status_val == ReviewStatus.NEEDS_WORK.value:
                    counts = _format_severity_counts(fe.suggestions)
                    if counts:
                        item += f" \u2014 {counts}"
                lines.append(item)

    # Skipped Files section (informational, before narrative)
    if state.skippedFiles:
        not_on_branch = sum(1 for sf in state.skippedFiles if sf.reason == "not_on_branch")
        already_reviewed = sum(1 for sf in state.skippedFiles if sf.reason == "already_reviewed")
        total = len(state.skippedFiles)
        parts = []
        if not_on_branch:
            parts.append(f"{not_on_branch} not on branch")
        if already_reviewed:
            parts.append(f"{already_reviewed} already reviewed")
        detail = f" ({', '.join(parts)})" if parts else ""
        lines.extend(["", f"*Skipped files:* {total}{detail}"])

    # Review Narrative section
    lines.extend(["", "### Review Narrative", ""])
    narrative = state.overallSummary.narrativeSummary
    lines.append(narrative if narrative else "Awaiting review...")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subsequent-comment header utilities
# ---------------------------------------------------------------------------

# Regex matching the top-level summary heading lines that should be rewritten
_SUMMARY_HEADING_RE = re.compile(r"^## (?:File Review Summary: .+|Overall PR Review Summary)\s*$")


def _build_subsequent_header(commit_hash: str | None, commit_url: str | None) -> str:
    """Build the compact ``### Commit:`` header for subsequent/reply comments.

    Fallback chain (FR-008):
      - Both hash and URL → ``### Commit: [<short_hash>](<commit_url>)``
      - Hash only (no URL) → ``### Commit: <short_hash>``
      - No hash → ``### Commit: unknown``
    """
    if commit_hash and commit_url:
        short_hash = commit_hash[:SHORT_HASH_LENGTH]
        return f"### Commit: [{short_hash}]({commit_url})"
    elif commit_hash:
        short_hash = commit_hash[:SHORT_HASH_LENGTH]
        return f"### Commit: {short_hash}"
    else:
        return "### Commit: unknown"


def rewrite_header_for_subsequent(
    content: str,
    commit_hash: str | None,
    commit_url: str | None,
) -> str:
    """Rewrite the top heading of previously rendered summary content for use as a reply.

    Replaces the first line matching ``## File Review Summary: ...`` or
    ``## Overall PR Review Summary`` with the compact ``### Commit:`` header.
    If the first line does not match a known summary heading, the content is
    returned unchanged.

    Args:
        content: Previously rendered summary markdown content.
        commit_hash: Full commit hash (first 7 chars used for display).
        commit_url: URL to the commit. When ``None``, falls back per FR-008.

    Returns:
        Content with the heading replaced (or unchanged if no match).
    """
    if not content:
        return content

    lines = content.split("\n", 1)
    first_line = lines[0]

    if not _SUMMARY_HEADING_RE.match(first_line):
        return content

    new_header = _build_subsequent_header(commit_hash, commit_url)
    if len(lines) > 1:
        return new_header + "\n" + lines[1]
    return new_header


def validate_comment_header(content: str, is_subsequent: bool) -> bool:
    """Validate whether a comment's header matches the expected format for its position.

    Args:
        content: The full markdown content of the comment.
        is_subsequent: Whether this is a subsequent (reply) comment or a top-level comment.

    Returns:
        True if the header format is valid for the given position, False otherwise.
    """
    if not content:
        return False

    first_line = content.split("\n", 1)[0]

    if is_subsequent:
        # Subsequent comments must start with ### Commit:
        return first_line.startswith("### Commit:")
    else:
        # Top-level comments must start with ## File Review Summary: or ## Overall PR Review Summary
        return bool(_SUMMARY_HEADING_RE.match(first_line))


def repair_subsequent_header(content: str, review_state: ReviewState) -> str:
    """Repair an invalid subsequent-comment header using ReviewState metadata.

    If the content starts with a top-level summary heading (``## ...``), replaces
    it with the compact ``### Commit:`` format using commit metadata from
    ``review_state``.

    Args:
        content: The markdown content with a potentially invalid header.
        review_state: ReviewState providing ``commitHash`` as the source of truth.

    Returns:
        Content with the header repaired (or unchanged if already valid).
    """
    if not content:
        return content

    first_line = content.split("\n", 1)[0]

    # Only repair if the header is a known top-level summary heading
    if not _SUMMARY_HEADING_RE.match(first_line):
        return content

    commit_hash = review_state.commitHash if review_state.commitHash else None
    # ReviewState does not carry a commit URL; use hash-only or unknown fallback
    return rewrite_header_for_subsequent(content, commit_hash, None)
