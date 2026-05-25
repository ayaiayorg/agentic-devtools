"""Tests for ResolveThreadsAction."""

from unittest.mock import MagicMock, call

from agentic_devtools.cli.ci.models import FinalizationResult, ReviewInfo
from agentic_devtools.cli.ci.pipeline.actions.resolve_threads import ResolveThreadsAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestResolveThreadsAction:
    """Tests for resolve threads action."""

    def test_skip_when_active_session(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, active_session=True, unresolved_threads=5)
        derived = DerivedState(snapshot)
        action = ResolveThreadsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "active" in result.details.lower()

    def test_skip_when_copilot_review_pending(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="passing", copilot_review_pending=True, unresolved_threads=3)
        derived = DerivedState(snapshot)
        action = ResolveThreadsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "pending" in result.details.lower()

    def test_skip_when_ci_not_passing(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="failing", unresolved_threads=3)
        derived = DerivedState(snapshot)
        action = ResolveThreadsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "ci is failing" in result.details.lower()

    def test_skip_when_no_threads(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="passing", unresolved_threads=0)
        derived = DerivedState(snapshot)
        action = ResolveThreadsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "no unresolved" in result.details.lower()

    def test_execute_when_threads_exist(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            active_session=False,
            ci_status="passing",
            copilot_review_pending=False,
            unresolved_threads=3,
        )
        derived = DerivedState(snapshot)
        action = ResolveThreadsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_skip_when_derived_pending_review_is_true(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="passing", copilot_review_pending=False, unresolved_threads=3)
        derived = DerivedState(snapshot)
        derived.set("copilot_review_pending", True)
        action = ResolveThreadsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "pending" in result.details.lower()

    def test_execute_calls_finalize(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="head123",
            base_branch="main",
            head_branch="feature",
            unresolved_threads=2,
            reviews=[
                ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old123"),
            ],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.finalize_post_repair.return_value = FinalizationResult(resolved_count=2, unresolved_count=0)
        action = ResolveThreadsAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert "2" in result.details
        provider.finalize_post_repair.assert_called_once()

    def test_execute_calls_finalize_for_all_prior_reviews(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="head123",
            base_branch="main",
            head_branch="feature",
            unresolved_threads=4,
            reviews=[
                ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old123"),
                ReviewInfo(id=12, user="Copilot", state="COMMENTED", commit_sha="old456"),
            ],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.finalize_post_repair.side_effect = [
            FinalizationResult(resolved_count=1, unresolved_count=1),
            FinalizationResult(resolved_count=2, unresolved_count=0),
        ]
        action = ResolveThreadsAction()

        result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        assert result.details == "Resolved 3 thread(s), 1 left open"
        assert derived.unresolved_threads == 1
        provider.finalize_post_repair.assert_has_calls(
            [
                call(
                    pr_number=1,
                    base_branch="main",
                    head_branch="feature",
                    head_sha="head123",
                    review_id=12,
                ),
                call(
                    pr_number=1,
                    base_branch="main",
                    head_branch="feature",
                    head_sha="head123",
                    review_id=10,
                ),
            ]
        )

    def test_execute_sets_derived_unresolved_threads(self) -> None:
        """execute() writes post-resolution unresolved count to derived state."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="head123",
            base_branch="main",
            head_branch="feature",
            unresolved_threads=3,
            reviews=[
                ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old123"),
            ],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.finalize_post_repair.return_value = FinalizationResult(resolved_count=2, unresolved_count=1)
        action = ResolveThreadsAction()
        action.execute(provider, snapshot, derived)
        # Derived state must reflect the post-resolution count, not the snapshot count.
        assert derived.unresolved_threads == 1

    def test_execute_reports_skipped_prior_reviews(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_sha="head123",
            base_branch="main",
            head_branch="feature",
            unresolved_threads=2,
            reviews=[
                ReviewInfo(id=11, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old123"),
                ReviewInfo(id=10, user="Copilot", state="COMMENTED", commit_sha="old456"),
            ],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.finalize_post_repair.side_effect = [
            FinalizationResult(skipped=True, reason="no_new_commit"),
            FinalizationResult(resolved_count=2, unresolved_count=0),
        ]
        action = ResolveThreadsAction()

        result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        assert result.details == "Resolved 2 thread(s), 0 left open; skipped 1 prior review(s)"
