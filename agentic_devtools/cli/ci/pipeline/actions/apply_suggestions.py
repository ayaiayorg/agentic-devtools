"""Apply suggestions action — auto-applies review suggestions before repair dispatch.

Supports two types of suggestions:
1. Standard ``suggestion`` fenced blocks in comment bodies (via GraphQL)
2. Copilot "Suggested changeset" diffs (via page HTML scraping fallback)

The page-scraping fallback activates when no standard suggestion blocks are found
but an actionable Copilot review exists with inline comments.
"""

from __future__ import annotations

import logging
import os

from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.pipeline.suggestions import (
    ApplySuggestionsResult,
    apply_suggestions_with_bisection,
    fetch_applicable_suggestions,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)

# Safety threshold: do not apply more than this many suggestions in one action
_MAX_SUGGESTIONS_THRESHOLD = 50

# Maximum number of autofix cycles per PR before permanently skipping
_MAX_AUTOFIX_CYCLES = 20


class ApplySuggestionsAction:
    """Apply autofixable review suggestions via GraphQL before repair dispatch.

    Positioned after GuardsAction and PublishAction, before DispatchRepairAction.
    When suggestions are successfully applied, sets ``invalidates_snapshot = True``
    to trigger a snapshot refresh for downstream actions.

    Preconditions:
    - Actionable Copilot review exists with suggestions
    - Suggestion count ≤ threshold (50)
    - Not blocked by guards (fork, privileged paths, etc.)
    """

    @property
    def name(self) -> str:
        return "apply_suggestions"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether suggestions can be applied.

        Checks that:
        1. Feature is enabled via ENABLE_AUTO_APPLY_SUGGESTIONS env var
        2. There is an actionable Copilot review with inline comments
        3. The review has suggestions that can be applied
        """
        preconditions: dict[str, bool] = {}

        # Feature gate: repository variable must explicitly enable this action.
        # Defaults to disabled for safety — operator must set ENABLE_AUTO_APPLY_SUGGESTIONS=true
        # in repository Actions variables to activate.
        enabled = os.environ.get("ENABLE_AUTO_APPLY_SUGGESTIONS", "").lower() == "true"
        preconditions["feature_enabled"] = enabled
        if not enabled:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Auto-apply suggestions disabled (ENABLE_AUTO_APPLY_SUGGESTIONS != 'true')",
            )

        # Must have an actionable review:
        # - CHANGES_REQUESTED is actionable when a Copilot review exists
        # - COMMENTED is actionable only when inline count is non-zero (or unknown=-1)
        # - OR: unresolved threads exist from prior commits (suggestions may
        #   still be applicable even though the review is no longer on HEAD)
        has_actionable_review = snapshot.copilot_review_id > 0 and (
            snapshot.review_state == "CHANGES_REQUESTED"
            or (snapshot.review_state == "COMMENTED" and snapshot.copilot_review_inline_count != 0)
        )
        has_unresolved_prior_threads = snapshot.unresolved_threads > 0
        preconditions["has_actionable_review"] = has_actionable_review or has_unresolved_prior_threads

        if not has_actionable_review and not has_unresolved_prior_threads:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="No actionable Copilot review with suggestions",
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details="Actionable review detected — will attempt to apply suggestions",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Execute suggestion application via GraphQL.

        1. Check autofix cycle limit
        2. Fetch all applicable suggestions
        3. Check threshold
        4. Attempt batch apply
        5. Fall back to bisection on conflict
        6. Populate ExclusionContext for downstream actions
        """
        # Check autofix cycle limit — prevents infinite loops where review
        # suggestions repeatedly fail CI after being applied.
        # _count_prior_autofix_comments handles its own exceptions (fail-open, returns 0).
        prior_autofix_count = _count_prior_autofix_comments(provider, snapshot.pr_number)
        if prior_autofix_count >= _MAX_AUTOFIX_CYCLES:
            logger.warning(
                "PR #%d: Autofix cycle limit reached (%d/%d) — skipping",
                snapshot.pr_number,
                prior_autofix_count,
                _MAX_AUTOFIX_CYCLES,
            )
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions={"cycle_limit_reached": True},
                details=f"Autofix cycle limit reached ({prior_autofix_count}/{_MAX_AUTOFIX_CYCLES})",
            )

        # Fetch applicable suggestions (standard ```suggestion blocks via GraphQL)
        fetch_failed = False
        try:
            suggestions, pr_node_id = fetch_applicable_suggestions(provider, snapshot.pr_number)
        except Exception as exc:
            fetch_failed = True
            logger.warning("PR #%d: Failed to fetch suggestions: %s", snapshot.pr_number, exc)
            suggestions = []
            pr_node_id = ""

        # Fallback: try Copilot "Suggested changeset" diffs from page HTML
        # These are not stored in the comment body — they're embedded in the
        # PR page as React partial JSON. This handles Copilot code review
        # suggestions that use the proprietary "autofix" format.
        if not suggestions:
            fallback_failed = False
            try:
                fallback_result = _apply_copilot_autofix_suggestions(provider, snapshot)
            except Exception as exc:
                fallback_failed = True
                logger.warning(
                    "PR #%d: Copilot autofix fallback failed: %s",
                    snapshot.pr_number,
                    exc,
                )
                fallback_result = None

            if fallback_result is not None:
                # Set exclusion context so dispatch_repair skips applied comments.
                # Since apply_pr_suggestions already resolves threads, the primary
                # mechanism is thread resolution. ExclusionContext is supplementary.
                if fallback_result.get("exclusion_ctx"):
                    derived.set("exclusion_context", fallback_result["exclusion_ctx"])
                # Signal to resolve_threads to skip SDK evaluation — remaining
                # threads haven't been addressed yet (no repair has run).
                action_result = fallback_result["action_result"]
                if action_result.decision == ActionDecision.EXECUTE:
                    derived.set("autofix_applied_this_iteration", True)
                return action_result

            # Neither approach found suggestions
            failed_sources = []
            if fetch_failed:
                failed_sources.append("GraphQL fetch")
            if fallback_failed:
                failed_sources.append("autofix fallback")
            details = (
                "No applicable suggestions found; "
                f"suggestion discovery failed earlier ({', '.join(failed_sources)}), see logs"
                if failed_sources
                else "No applicable suggestions found"
            )
            logger.info("PR #%d: %s", snapshot.pr_number, details)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions={"suggestions_found": False},
                details=details,
            )

        # Check threshold (FR-011)
        if len(suggestions) > _MAX_SUGGESTIONS_THRESHOLD:
            logger.warning(
                "PR #%d: Suggestion count %d exceeds threshold %d — deferring to repair",
                snapshot.pr_number,
                len(suggestions),
                _MAX_SUGGESTIONS_THRESHOLD,
            )
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions={"suggestions_found": True, "within_threshold": False},
                details=f"Suggestion count ({len(suggestions)}) exceeds threshold ({_MAX_SUGGESTIONS_THRESHOLD})",
            )

        suggestion_ids = [s.suggestion_id for s in suggestions]
        logger.info(
            "PR #%d: Applying %d suggestions via createCommitOnBranch",
            snapshot.pr_number,
            len(suggestion_ids),
        )

        # Apply suggestions — batch first, bisection fallback on conflict
        try:
            result = apply_suggestions_with_bisection(
                provider,
                pr_node_id,
                suggestion_ids,
                suggestions=suggestions,
                head_ref=snapshot.head_branch,
                head_oid=snapshot.head_sha,
            )
        except Exception as exc:
            logger.warning("PR #%d: Failed to apply suggestions: %s", snapshot.pr_number, exc)
            # Return SKIP (not FAILED) to avoid halting pipeline per FR-010
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions={"suggestions_found": True, "within_threshold": True},
                details=f"Failed to apply suggestions: {exc}",
            )

        # If nothing was applied, return SKIP
        if not result.applied_ids:
            logger.info(
                "PR #%d: No suggestions could be applied (error=%s)",
                snapshot.pr_number,
                result.error,
            )
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions={"suggestions_found": True, "within_threshold": True},
                details=f"No suggestions applied: {result.error or 'all conflicted'}",
            )

        # Build ExclusionContext — only mark a comment as resolved when ALL its
        # applicable suggestions were successfully applied. Partial application
        # (some suggestions conflicted/skipped) leaves the comment visible to the
        # repair agent so the remaining feedback is not silently dropped.
        applied_suggestion_ids_set = set(result.applied_ids)

        comment_suggestions: dict[int, list[str]] = {}
        for s in suggestions:
            comment_suggestions.setdefault(s.comment_database_id, []).append(s.suggestion_id)

        resolved_comment_ids: set[int] = {
            comment_id
            for comment_id, sids in comment_suggestions.items()
            if all(sid in applied_suggestion_ids_set for sid in sids)
        }

        exclusion_ctx = ExclusionContext(resolved_comment_ids=resolved_comment_ids)
        derived.set("exclusion_context", exclusion_ctx)

        logger.info(
            "PR #%d: Applied %d suggestions, skipped %d (commits=%s)",
            snapshot.pr_number,
            len(result.applied_ids),
            len(result.skipped_ids),
            result.commit_shas,
        )

        # Post summary comment (FR — User Story 5)
        _post_summary_comment(provider, snapshot.pr_number, result)

        # Signal to resolve_threads to skip SDK evaluation — remaining
        # threads haven't been addressed yet (no repair has run).
        derived.set("autofix_applied_this_iteration", True)

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions={"suggestions_found": True, "within_threshold": True},
            details=(
                f"Applied {len(result.applied_ids)} suggestions"
                f" (skipped={len(result.skipped_ids)}, commits={len(result.commit_shas)})"
            ),
            invalidates_snapshot=True,
        )


def _post_summary_comment(
    provider: CIPlatformProvider,
    pr_number: int,
    result: ApplySuggestionsResult,
) -> None:
    """Post a summary comment about applied suggestions."""
    if not result.applied_ids:
        return

    applied_count = len(result.applied_ids)
    skipped_count = len(result.skipped_ids)

    body_parts = [
        f"🔧 **Auto-applied {applied_count} suggestion{'s' if applied_count != 1 else ''}**",
    ]

    if result.commit_shas:
        commit_shas = [sha for sha in result.commit_shas if sha != "pending_refresh"]
        if commit_shas:
            sha_list = ", ".join(f"`{sha[:7]}`" for sha in commit_shas)
            commit_word = "commit" if len(commit_shas) == 1 else "commits"
            body_parts.append(f" in {commit_word} {sha_list}")

    if skipped_count > 0:
        suffix = "s" if skipped_count != 1 else ""
        skip_reason = "conflict/outdated"
        if result.error:
            first_nonempty_line = next((line.strip() for line in result.error.splitlines() if line.strip()), "")
            if first_nonempty_line:
                skip_reason = first_nonempty_line
        body_parts.append(f"\n\n⚠️ {skipped_count} suggestion{suffix} could not be applied ({skip_reason}).")

    body = "".join(body_parts)

    try:
        provider.post_comment(pr_number, body)
    except Exception as exc:
        logger.warning("PR #%d: Failed to post suggestion summary comment: %s", pr_number, exc)


def _count_prior_autofix_comments(
    provider: CIPlatformProvider,
    pr_number: int,
) -> int:
    """Count prior autofix summary comments to enforce cycle limit.

    Counts PR issue comments containing the distinctive autofix summary prefix.
    This provides a persistent, cross-run counter without requiring external state.
    """
    try:
        comments = provider.list_issue_comments(pr_number)
    except Exception:
        return 0

    count = 0
    for comment in comments:
        body = getattr(comment, "body", "") or ""
        if "🔧 **Auto-applied" in body:
            count += 1
    return count


def _apply_copilot_autofix_suggestions(
    provider: CIPlatformProvider,
    snapshot: PRStateSnapshot,
) -> dict | None:
    """Try to apply Copilot 'Suggested changeset' diffs via page HTML scraping.

    This is the fallback for when standard ```suggestion blocks are not found.
    Copilot code review uses a proprietary "autofix" format that stores suggestion
    diffs in embedded React partial JSON within the PR page HTML.

    Returns a dict with ``action_result`` (ActionResult) and ``exclusion_ctx``
    (ExclusionContext or None) if suggestions were found and processed, or None
    if no Copilot autofix suggestions exist.

    On any error, returns None (fail-open, per FR-010 — does not halt the pipeline).
    """
    from agentic_devtools.cli.github.apply_thread_autofix import apply_pr_suggestions

    # Resolve repo name from provider or environment
    repo = getattr(provider, "_repo", None) or os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        logger.warning(
            "PR #%d: Copilot autofix fallback skipped — repo could not be determined "
            "(set GITHUB_REPOSITORY or ensure provider._repo is populated)",
            snapshot.pr_number,
        )
        return None

    logger.info(
        "PR #%d: No standard suggestion blocks found, trying Copilot autofix fallback",
        snapshot.pr_number,
    )

    try:
        result = apply_pr_suggestions(
            pr_number=snapshot.pr_number,
            repo=repo,
            comment_ids=None,
            message="Apply suggestions from code review",
            resolve=True,
        )
    except SystemExit:
        # apply_pr_suggestions may call sys.exit on fatal errors (e.g., gh not found)
        # In pipeline context, treat as non-fatal skip
        logger.warning(
            "PR #%d: Copilot autofix fallback exited — treating as skip",
            snapshot.pr_number,
        )
        return None
    except Exception as exc:
        logger.warning(
            "PR #%d: Copilot autofix fallback error: %s",
            snapshot.pr_number,
            exc,
        )
        return None

    applied = result.get("applied", 0)
    skipped = result.get("skipped", 0)
    commit = result.get("commit")

    if applied == 0 and skipped == 0:
        # No Copilot autofix suggestions found at all
        return None

    logger.info(
        "PR #%d: Copilot autofix — applied %d, skipped %d, commit=%s",
        snapshot.pr_number,
        applied,
        skipped,
        commit[:12] if commit else "none",
    )

    # Threads are already resolved by apply_pr_suggestions via GraphQL.
    # The snapshot refresh (triggered by invalidates_snapshot=True) will pick
    # up the resolved state. No ExclusionContext is needed here.
    exclusion_ctx = None

    if applied > 0:
        action_result = ActionResult(
            name="apply_suggestions",
            decision=ActionDecision.EXECUTE,
            preconditions={"suggestions_found": True, "within_threshold": True},
            details=(
                f"Copilot autofix: applied {applied} suggestion(s)"
                f"{f', skipped {skipped}' if skipped else ''}"
                f" (commit={commit[:12] if commit else 'none'})"
            ),
            invalidates_snapshot=True,
        )
    else:
        action_result = ActionResult(
            name="apply_suggestions",
            decision=ActionDecision.SKIP,
            preconditions={"suggestions_found": True, "within_threshold": True},
            details=f"Copilot autofix: all {skipped} suggestions conflicted/stale",
        )

    return {"action_result": action_result, "exclusion_ctx": exclusion_ctx}
