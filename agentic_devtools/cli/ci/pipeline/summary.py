"""Summary comment rendering and posting for the pipeline."""

from __future__ import annotations

import html
import logging
import os
import re

from agentic_devtools.cli.ci.pipeline.models import (
    ActionDecision,
    ActionResult,
    PipelineRunSummary,
)
from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

SUMMARY_SENTINEL = "<!-- agdt:ai-pr-loop-summary -->"
SUMMARY_COLLAPSED_SENTINEL = "<!-- agdt:ai-pr-loop-summary-collapsed -->"
SUMMARY_FALLBACK_MARKER = f"{SUMMARY_SENTINEL}\n\n**🤖 AI PR Loop Run"


def _sanitize_cell(value: str) -> str:
    """Sanitize a Markdown table cell value.

    Replaces newlines with <br> and escapes pipe characters to prevent
    broken table formatting when values come from exception messages or
    multi-line details strings.
    """
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    escaped = html.escape(normalized, quote=False)
    return escaped.replace("|", "\\|").replace("\n", "<br>")


def _normalize_summary_header_text(value: str) -> str:
    """Normalize markdown-heavy header content for HTML <summary> text."""
    normalized = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1: \2", value)
    normalized = normalized.replace("**", "").replace("`", "")
    return html.escape(normalized.strip(), quote=False)


def _is_editable_summary_comment_author(*, author: str, actor: str) -> bool:
    """Return True when a summary comment author is likely editable by this run.

    Fails closed: an empty/unknown author is treated as not editable to avoid
    accidentally editing comments posted by a deleted or anonymous user.
    """
    normalized_author = author.strip().lower()
    normalized_actor = actor.strip().lower()
    if not normalized_author:
        return False
    return normalized_author.endswith("[bot]") or (bool(normalized_actor) and normalized_author == normalized_actor)


_DECISION_ICONS = {
    ActionDecision.EXECUTE: "✅",
    ActionDecision.SKIP: "⬜",
    ActionDecision.BLOCKED: "🚫",
    ActionDecision.BLOCKED_BY_GUARD: "🚫",
    ActionDecision.FAILED: "❌",
}

_DECISION_LABELS = {
    ActionDecision.EXECUTE: "**executed**",
    ActionDecision.SKIP: "skipped",
    ActionDecision.BLOCKED: "blocked",
    ActionDecision.BLOCKED_BY_GUARD: "blocked (guards)",
    ActionDecision.FAILED: "**failed**",
}


def render_summary_comment(summary: PipelineRunSummary) -> str:
    """Render the pipeline run summary as a markdown comment.

    Includes:
    - Link to workflow run
    - Action evaluation table
    - Collapsed state snapshot details
    """
    lines: list[str] = []

    # Sentinel for identification
    lines.append(SUMMARY_SENTINEL)
    lines.append("")

    # Header with link
    if summary.run_url:
        lines.append(f"**🤖 AI PR Loop Run** — [View Logs]({summary.run_url})")
    else:
        lines.append("**🤖 AI PR Loop Run**")
    lines.append("")

    # Action table
    lines.append("| Action | Preconditions | Result |")
    lines.append("|--------|--------------|--------|")

    for result in summary.results:
        icon = _DECISION_ICONS.get(result.decision, "❓")
        label = _DECISION_LABELS.get(result.decision, result.decision.value)
        precond_text = _sanitize_cell(_format_preconditions(result))
        detail_parts: list[str] = []
        if result.details and result.decision in {
            ActionDecision.EXECUTE,
            ActionDecision.FAILED,
            ActionDecision.SKIP,
            ActionDecision.BLOCKED,
            ActionDecision.BLOCKED_BY_GUARD,
        }:
            detail_parts.append(_sanitize_cell(result.details))
        if result.error and result.decision == ActionDecision.FAILED:
            detail_parts.append(f"error: {_sanitize_cell(result.error)}")
        detail_text = f" ({'; '.join(detail_parts)})" if detail_parts else ""
        lines.append(f"| {_sanitize_cell(result.name)} | {icon} {precond_text} | {label}{detail_text} |")

    lines.append("")

    # State snapshot (collapsed)
    if summary.snapshot:
        lines.append("<details><summary>State snapshot</summary>")
        lines.append("")
        lines.append(_render_state_snapshot(summary.snapshot))
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def _format_preconditions(result: ActionResult) -> str:
    """Format preconditions into a short summary string."""
    if not result.preconditions:
        return "—"

    # Show the key preconditions concisely
    parts = []
    for key, value in result.preconditions.items():
        if not value:
            parts.append(f"✗ {key}")
            break
    if not parts:
        parts.append("all passed")

    return ", ".join(parts)[:60]


def _render_state_snapshot(snapshot: PRStateSnapshot) -> str:
    """Render state snapshot as bullet list."""
    head_sha_short = _sanitize_cell(snapshot.head_sha[:7])
    review_state = _sanitize_cell(snapshot.review_state or "none")
    inline_count = snapshot.copilot_review_inline_count
    inline_count_unknown = inline_count is None or inline_count < 0
    show_inline_suffix = (
        snapshot.review_state == "COMMENTED" or inline_count_unknown or (inline_count is not None and inline_count > 0)
    )
    if show_inline_suffix:
        if inline_count_unknown:
            inline_suffix = " (inline unknown)"
        else:
            inline_suffix = f" ({_sanitize_cell(str(inline_count))} inline)"
    else:
        inline_suffix = ""
    labels = _sanitize_cell(", ".join(snapshot.labels) if snapshot.labels else "none")
    lines = [
        f"- HEAD: `{head_sha_short}`",
        f"- Commits above merge-base: {_sanitize_cell(str(snapshot.commit_count))}",
        "- Copilot session active: N/A",
        f"- Copilot review on HEAD: {review_state}{inline_suffix}",
        f"- CI: {_sanitize_cell(snapshot.ci_status)}",
        f"- Unresolved threads: {_sanitize_cell(str(snapshot.unresolved_threads))}",
        f"- Draft: {_sanitize_cell(str(snapshot.is_draft))}",
        f"- Labels: {labels}",
    ]
    return "\n".join(lines)


def collapse_prior_summaries(provider: CIPlatformProvider, pr_number: int) -> int:
    """Find and collapse prior summary comments.

    Finds comments with the active sentinel and wraps them in <details>
    blocks, replacing the sentinel with the collapsed sentinel.

    Returns:
        Number of comments collapsed.
    """
    collapsed_count = 0

    list_issue_comments = getattr(provider, "list_issue_comments", None)
    if callable(list_issue_comments):
        actor = os.environ.get("GITHUB_ACTOR", "").strip().lower()
        comments = list_issue_comments(pr_number)
        for comment in comments:
            body = comment.body or ""
            if SUMMARY_SENTINEL not in body or SUMMARY_COLLAPSED_SENTINEL in body:
                continue
            # Same safeguards as the fallback path: only collapse comments that
            # start with the sentinel and contain the expected pipeline header,
            # to avoid editing unrelated bot comments that happen to quote the marker.
            if not body.startswith(SUMMARY_SENTINEL) or "AI PR Loop Run" not in body:
                logger.info(
                    "PR #%d: Skipping comment %d — body does not match expected pipeline format",
                    pr_number,
                    comment.id,
                )
                continue
            author = comment.author or ""
            if not _is_editable_summary_comment_author(author=author, actor=actor):
                logger.info("PR #%d: Skipping non-bot summary marker comment %d", pr_number, comment.id)
                continue
            collapsed_body = body.replace(SUMMARY_SENTINEL, SUMMARY_COLLAPSED_SENTINEL)
            header_line = "AI PR Loop Run (prior)"
            for line in collapsed_body.split("\n"):
                if "AI PR Loop Run" in line:
                    header_line = _normalize_summary_header_text(line)
                    break
            wrapped_body = (
                f"{SUMMARY_COLLAPSED_SENTINEL}\n"
                f"<details><summary>{header_line}</summary>\n\n"
                f"{collapsed_body.replace(SUMMARY_COLLAPSED_SENTINEL, '').strip()}\n"
                f"</details>"
            )
            try:
                provider.update_comment(comment.id, wrapped_body)
                collapsed_count += 1
            except Exception as exc:
                logger.warning("PR #%d: Failed to collapse comment %d: %s", pr_number, comment.id, exc)
        return collapsed_count

    # Fallback: use provider's find_comment to locate summaries.
    # Use a stricter marker than SUMMARY_SENTINEL to avoid false-positives on
    # unrelated comments that merely quote/include the sentinel text.
    # We may need to iterate; find_comment returns first match
    while True:
        found = provider.find_comment(pr_number, SUMMARY_FALLBACK_MARKER)
        if found is None:
            break

        comment_id, body = found

        # Safeguard: only collapse comments whose body starts with the sentinel and
        # contains the expected pipeline header, to avoid editing unrelated user
        # comments that happen to include the marker text.
        if not body.startswith(SUMMARY_SENTINEL) or "AI PR Loop Run" not in body:
            logger.info(
                "PR #%d: Skipping comment %d in fallback path — body does not match expected pipeline format",
                pr_number,
                comment_id,
            )
            break

        # Replace sentinel and wrap in details
        collapsed_body = body.replace(SUMMARY_SENTINEL, SUMMARY_COLLAPSED_SENTINEL)
        # Extract the header for the details summary
        header_line = "AI PR Loop Run (prior)"
        for line in collapsed_body.split("\n"):
            if "AI PR Loop Run" in line:
                header_line = _normalize_summary_header_text(line)
                break

        wrapped_body = (
            f"{SUMMARY_COLLAPSED_SENTINEL}\n"
            f"<details><summary>{header_line}</summary>\n\n"
            f"{collapsed_body.replace(SUMMARY_COLLAPSED_SENTINEL, '').strip()}\n"
            f"</details>"
        )

        try:
            provider.update_comment(comment_id, wrapped_body)
            collapsed_count += 1
        except Exception as exc:
            logger.warning("PR #%d: Failed to collapse comment %d: %s", pr_number, comment_id, exc)
            break

    return collapsed_count


def post_summary_comment(
    provider: CIPlatformProvider,
    pr_number: int,
    summary: PipelineRunSummary,
) -> bool:
    """Post a summary comment and collapse prior summaries.

    Returns True on success, False on failure (non-fatal).
    """
    # Collapse prior summaries first
    try:
        collapsed = collapse_prior_summaries(provider, pr_number)
        if collapsed:
            logger.info("PR #%d: Collapsed %d prior summary comment(s)", pr_number, collapsed)
    except Exception as exc:
        logger.warning("PR #%d: Failed to collapse prior summaries: %s", pr_number, exc)

    # Render and post new comment
    comment_body = render_summary_comment(summary)

    try:
        provider.post_comment(pr_number, comment_body)
        logger.info("PR #%d: Posted pipeline summary comment", pr_number)
        return True
    except Exception as exc:
        logger.warning("PR #%d: Failed to post summary comment: %s", pr_number, exc)
        return False
