"""Tests for MergeAction."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import ReviewInfo
from agentic_devtools.cli.ci.pipeline.actions.merge import MergeAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


def _ready_snapshot(**overrides: object) -> PRStateSnapshot:
    """Return a snapshot with all merge preconditions satisfied."""
    defaults: dict = {
        "pr_number": 1,
        "is_draft": False,
        "has_approval_on_head": True,
        "ci_status": "passing",
        "labels": ["ai-auto-merge-allowed"],
        "mergeable": True,
        "unresolved_threads": 0,
        "copilot_review_pending": False,
        "review_state": "APPROVED",
        "copilot_review_id": 99,
        "copilot_review_inline_count": 0,
    }
    defaults.update(overrides)
    return PRStateSnapshot(**defaults)


class TestMergeAction:
    """Tests for merge action evaluation."""

    def test_skip_when_draft(self) -> None:
        """Merge is skipped when PR is a draft."""
        snapshot = _ready_snapshot(is_draft=True)
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "draft" in result.details.lower()

    def test_skip_when_draft_via_derived(self) -> None:
        """Merge is skipped when is_draft is set on DerivedState (e.g., publish failed)."""
        snapshot = _ready_snapshot(is_draft=False)
        derived = DerivedState(snapshot)
        derived.set("is_draft", True)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "draft" in result.details.lower()

    def test_not_draft_via_derived_allows_proceed(self) -> None:
        """When derived marks is_draft=False (publish succeeded), not_draft precondition passes."""
        snapshot = _ready_snapshot(is_draft=True)
        derived = DerivedState(snapshot)
        derived.set("is_draft", False)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        # Should proceed past draft check; will fail at approval check
        assert result.preconditions.get("not_draft") is True

    def test_skip_when_not_approved(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=False,
            ci_status="passing",
            labels=["ai-auto-merge-allowed"],
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "not approved" in result.details.lower()

    def test_skip_when_ci_not_passing(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=True,
            ci_status="pending",
            labels=["ai-auto-merge-allowed"],
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    def test_skip_when_no_label(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=True,
            ci_status="passing",
            labels=[],
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "label" in result.details.lower()

    def test_skip_when_not_mergeable(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=True,
            ci_status="passing",
            labels=["ai-auto-merge-allowed"],
            mergeable=False,
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "not mergeable" in result.details.lower()

    def test_skip_when_unresolved_threads(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            has_approval_on_head=True,
            ci_status="passing",
            labels=["ai-auto-merge-allowed"],
            mergeable=True,
            unresolved_threads=1,
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    def test_skip_when_derived_unresolved_threads_nonzero(self) -> None:
        """Merge is blocked when DerivedState overrides unresolved_threads to > 0."""
        snapshot = _ready_snapshot(unresolved_threads=0)
        derived = DerivedState(snapshot)
        derived.set("unresolved_threads", 1)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "unresolved" in result.details.lower()

    def test_proceed_when_derived_clears_unresolved_threads(self) -> None:
        """Merge can proceed when DerivedState sets unresolved_threads to 0."""
        snapshot = _ready_snapshot(unresolved_threads=3)  # stale snapshot value
        derived = DerivedState(snapshot)
        derived.set("unresolved_threads", 0)  # ResolveThreadsAction updated this
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.preconditions.get("no_unresolved_threads") is True

    def test_skip_when_review_pending(self) -> None:
        """Merge is skipped when Copilot review is still pending."""
        snapshot = _ready_snapshot(copilot_review_pending=True)
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "pending" in result.details.lower()

    def test_skip_when_review_pending_via_derived(self) -> None:
        """Merge is skipped when copilot_review_pending is set via derived state."""
        snapshot = _ready_snapshot(copilot_review_pending=False)
        derived = DerivedState(snapshot)
        derived.set("copilot_review_pending", True)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "pending" in result.details.lower()

    def test_skip_when_non_copilot_changes_requested_on_head(self) -> None:
        snapshot = _ready_snapshot(
            head_sha="head-sha",
            reviews=[ReviewInfo(id=20, user="alice", state="CHANGES_REQUESTED", commit_sha="head-sha")],
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "requested changes" in result.details.lower()

    def test_skip_when_no_copilot_review(self) -> None:
        """Merge is skipped when no Copilot review exists on HEAD."""
        snapshot = _ready_snapshot(review_state="", copilot_review_id=0)
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "no copilot review" in result.details.lower()

    def test_skip_when_review_changes_requested(self) -> None:
        """Merge is skipped when Copilot review is CHANGES_REQUESTED."""
        snapshot = _ready_snapshot(review_state="CHANGES_REQUESTED", copilot_review_id=5)
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "actionable" in result.details.lower()

    def test_skip_when_review_commented_with_inline(self) -> None:
        """Merge is skipped when Copilot review is COMMENTED with inline comments."""
        snapshot = _ready_snapshot(
            review_state="COMMENTED",
            copilot_review_id=5,
            copilot_review_inline_count=3,
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "actionable" in result.details.lower()

    def test_execute_when_all_conditions_met(self) -> None:
        snapshot = _ready_snapshot()
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_when_review_commented_no_inline(self) -> None:
        """COMMENTED with 0 inline comments is considered clean."""
        snapshot = _ready_snapshot(
            review_state="COMMENTED",
            copilot_review_id=5,
            copilot_review_inline_count=0,
        )
        derived = DerivedState(snapshot)
        action = MergeAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_calls_provider(self) -> None:
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123", commit_count=1)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = MergeAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        provider.merge_pr.assert_called_once_with(42, "sha123", "rebase")

    def test_execute_uses_squash_when_multi_commit(self) -> None:
        """MergeAction uses squash merge when commit_count > 1."""
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123", commit_count=3, title="Fix bug")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = MergeAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert "squash" in result.details.lower()
        provider.merge_pr.assert_called_once_with(
            42, "sha123", "squash", commit_title="Fix bug (#42)"
        )

    def test_execute_uses_clean_fallback_title_for_squash(self) -> None:
        """Fallback squash title does not duplicate PR number when PR title is missing."""
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123", commit_count=3, title="")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = MergeAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        provider.merge_pr.assert_called_once_with(42, "sha123", "squash", commit_title="PR #42")

    def test_execute_uses_rebase_when_single_commit(self) -> None:
        """MergeAction uses rebase merge when commit_count == 1."""
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123", commit_count=1)
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = MergeAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert "rebase" in result.details.lower()
        provider.merge_pr.assert_called_once_with(42, "sha123", "rebase")

    def test_execute_uses_rebase_when_commit_count_default(self) -> None:
        """MergeAction falls back to rebase when commit_count is default (1)."""
        snapshot = PRStateSnapshot(pr_number=42, head_sha="sha123")
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = MergeAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        provider.merge_pr.assert_called_once_with(42, "sha123", "rebase")
