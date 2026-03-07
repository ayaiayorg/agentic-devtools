"""Verdict protocol for multi-model PR file reviews.

Implements the verdict recording logic when a secondary or tertiary reviewer
model completes its review of a file.  The three verdict types are:

- **Agree**: Model concurs with the primary review.  Only the Model Review
  Progress table is updated; no addendum is appended.
- **Supplement**: Model concurs but has additional findings.  An addendum
  section is appended to the main comment.
- **Disagree**: Model disputes one or more findings.  An addendum section is
  appended and the file is marked as requiring consolidation.

All verdicts update the per-model entry in ``FileEntry.modelVerdicts`` and
persist the change to ``review-state.json``.
"""

from typing import List, Optional

from .review_attribution import SHORT_HASH_LENGTH, get_model_icon
from .review_state import (
    COMPLETE_STATUSES,
    ConsolidationStatus,
    FileEntry,
    ModelVerdict,
    ReviewState,
    ReviewStatus,
    VerdictType,
)


def record_verdict(
    file_entry: FileEntry,
    model_id: str,
    verdict_type: str,
    status: str,
) -> ModelVerdict:
    """Record a model's verdict for a file.

    Updates the existing ``ModelVerdict`` entry in ``file_entry.modelVerdicts``
    (matched by ``model_id``) or creates a new one if not found.

    Args:
        file_entry: The ``FileEntry`` to update.
        model_id: Model identifier (e.g. "Gemini Pro 3.1").
        verdict_type: One of ``VerdictType.AGREE``, ``SUPPLEMENT``, ``DISAGREE``.
        status: Terminal review status for this model (``approved`` or ``needs_work``).

    Returns:
        The updated or newly created ``ModelVerdict``.

    Raises:
        ValueError: If ``verdict_type`` is not a valid verdict or ``status``
            is not a terminal status.
    """
    valid_verdicts = {VerdictType.AGREE, VerdictType.SUPPLEMENT, VerdictType.DISAGREE}
    if verdict_type not in valid_verdicts:
        raise ValueError(f"Invalid verdict_type: {verdict_type!r}. Must be one of {sorted(valid_verdicts)}")
    if status not in COMPLETE_STATUSES:
        raise ValueError(f"Invalid status: {status!r}. Must be a terminal status: {sorted(COMPLETE_STATUSES)}")

    existing = file_entry.get_model_verdict(model_id)
    if existing is not None:
        existing.status = status
        existing.verdictType = verdict_type
        return existing

    new_mv = ModelVerdict(modelId=model_id, status=status, verdictType=verdict_type)
    file_entry.modelVerdicts.append(new_mv)
    return new_mv


def compute_file_effective_status(file_entry: FileEntry) -> str:
    """Compute the effective aggregate status for a file based on model verdicts.

    Rules:
    - If no model verdicts exist, return the file's current status.
    - If any reviewer is still pending (not terminal), return ``in-progress``.
    - If all reviewers are complete and consolidation is needed but not complete,
      return ``in-progress``.
    - If all reviewers are complete and all agree (no supplements/disagreements),
      return the primary reviewer's terminal status.
    - If consolidation is complete, return the file's status (set by consolidator).

    Args:
        file_entry: The ``FileEntry`` to evaluate.

    Returns:
        Effective status string (a ``ReviewStatus`` value).
    """
    if not file_entry.modelVerdicts:
        return file_entry.status

    # Check if all reviewers are complete
    if not file_entry.all_reviewers_complete():
        return ReviewStatus.IN_PROGRESS.value

    # All reviewers complete — check if consolidation is needed
    if file_entry.needs_consolidation():
        if file_entry.consolidationStatus not in (ConsolidationStatus.COMPLETE, ConsolidationStatus.NOT_NEEDED):
            return ReviewStatus.IN_PROGRESS.value
        # Consolidation is complete — the file.status has been set by the consolidator
        return file_entry.status

    # All agree — use the primary reviewer's status (first model)
    primary = file_entry.modelVerdicts[0]
    return primary.status


def evaluate_consolidation_need(file_entry: FileEntry) -> str:
    """Evaluate whether consolidation is needed for a file after all reviewers complete.

    Must be called after the last reviewer's verdict is recorded.

    Args:
        file_entry: The ``FileEntry`` to evaluate.

    Returns:
        The consolidation status to set: ``not_needed`` or ``pending``.
    """
    if not file_entry.all_reviewers_complete():
        return ConsolidationStatus.NOT_NEEDED

    if file_entry.has_disagreements():
        return ConsolidationStatus.PENDING

    return ConsolidationStatus.NOT_NEEDED


def render_reviewer_addendum(
    model_name: str,
    verdict_type: str,
    commit_hash: Optional[str] = None,
    commit_url: Optional[str] = None,
    supplements: Optional[List[str]] = None,
    disagreements: Optional[List[str]] = None,
) -> str:
    """Render a reviewer addendum section for append-only main comment composition.

    This section is appended to the bottom of the file review main comment when
    a secondary/tertiary reviewer posts a supplement or disagree verdict.

    Args:
        model_name: Model identifier (e.g. "Gemini Pro 3.1").
        verdict_type: One of ``VerdictType.SUPPLEMENT`` or ``DISAGREE``.
        commit_hash: Commit hash reviewed (for attribution).
        commit_url: URL to the file at the reviewed commit.
        supplements: List of supplementary observations.
        disagreements: List of disagreement points.

    Returns:
        Markdown string for the addendum section.
    """
    icon = get_model_icon(model_name)
    short_hash = commit_hash[:SHORT_HASH_LENGTH] if commit_hash else "unknown"

    if commit_url:
        commit_ref = f"[`{short_hash}`]({commit_url})"
    else:
        commit_ref = f"`{short_hash}`"

    verdict_label = "Agree + Supplement" if verdict_type == VerdictType.SUPPLEMENT else "Disagree"

    lines = [
        "---",
        "",
        f"## Reviewer Addendum — {model_name}",
        "",
        f"🤖 *Reviewed by* {icon} **{model_name}** *at commit:* {commit_ref}",
        "",
        f"**Verdict:** {verdict_label}",
    ]

    if supplements:
        lines += ["", "### Supplements"]
        for item in supplements:
            lines.append(f"- {item}")

    if disagreements:
        lines += ["", "### Disagreements"]
        for item in disagreements:
            lines.append(f"- {item}")

    return "\n".join(lines)


def render_consolidation_decision(
    boss_model: str,
    final_verdict: str,
    resolved_from: List[str],
    commit_hash: Optional[str] = None,
    commit_url: Optional[str] = None,
    resolution_notes: Optional[List[str]] = None,
) -> str:
    """Render the consolidation decision section appended by the boss model.

    Args:
        boss_model: Consolidator model name.
        final_verdict: Terminal verdict string (e.g. "✅ Approved" or "📝 Needs Work").
        resolved_from: List of model names whose disagreements were resolved.
        commit_hash: Commit hash for attribution.
        commit_url: URL to the file at the reviewed commit.
        resolution_notes: List of resolution notes explaining the decision.

    Returns:
        Markdown string for the consolidation decision section.
    """
    short_hash = commit_hash[:SHORT_HASH_LENGTH] if commit_hash else "unknown"
    if commit_url:
        commit_ref = f"[`{short_hash}`]({commit_url})"
    else:
        commit_ref = f"`{short_hash}`"

    resolved_str = ", ".join(resolved_from) if resolved_from else "reviewers"

    lines = [
        "---",
        "",
        f"## Consolidation Decision — {boss_model}",
        "",
        f"*Resolved disagreements from: {resolved_str} at commit {commit_ref}*",
        "",
        f"**Final Verdict:** {final_verdict}",
    ]

    if resolution_notes:
        lines += ["", "### Resolution Notes"]
        for note in resolution_notes:
            lines.append(f"- {note}")

    return "\n".join(lines)


def initialize_model_verdicts(file_entry: FileEntry, reviewer_models: List[str]) -> None:
    """Initialize model verdict entries for all configured reviewer models.

    Called during scaffolding to pre-populate the Model Review Progress table
    with ``⏳ Awaiting Review`` entries for each model.

    Existing entries are preserved (idempotent).

    Args:
        file_entry: The ``FileEntry`` to update.
        reviewer_models: Ordered list of reviewer model identifiers.
    """
    existing_models = {mv.modelId for mv in file_entry.modelVerdicts}
    for model_id in reviewer_models:
        if model_id not in existing_models:
            file_entry.modelVerdicts.append(
                ModelVerdict(modelId=model_id, status=ReviewStatus.UNREVIEWED.value)
            )
