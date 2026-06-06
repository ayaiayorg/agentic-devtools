"""Tests for DispatchRepairAction."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.models import ReviewInfo
from agentic_devtools.cli.ci.pipeline.actions.dispatch_repair import DispatchRepairAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestDispatchRepairAction:
    """Tests for dispatch repair action evaluation."""

    def test_execute_when_ci_failing_even_with_active_session(self) -> None:
        """Session gate removed: active_session=True does NOT cause skip."""
        snapshot = PRStateSnapshot(pr_number=1, active_session=True, ci_status="failing")
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_preconditions_do_not_contain_no_active_session(self) -> None:
        """no_active_session key must be absent from preconditions."""
        snapshot = PRStateSnapshot(pr_number=1, ci_status="failing")
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert "no_active_session" not in result.preconditions

    def test_execute_when_review_actionable_with_active_session(self) -> None:
        """Session gate removed: actionable review + active_session=True returns EXECUTE."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            active_session=True,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_skip_when_ci_passing_and_no_review(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            review_state="APPROVED",
            copilot_review_id=1,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "no actionable" in result.details.lower() or "passing" in result.details.lower()

    def test_skip_message_includes_non_failing_ci_status(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="pending",
            review_state="APPROVED",
            copilot_review_id=1,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "ci_status=pending" in result.details.lower()

    def test_execute_when_ci_failing(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="failing",
            active_session=False,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_when_review_actionable(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            active_session=False,
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_when_prior_review_threads_are_stuck(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            head_sha="head123",
            copilot_review_id=0,
            unresolved_threads=2,
            reviews=[
                ReviewInfo(id=10, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old123"),
            ],
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert result.preconditions.get("stuck_prior_threads") is True

    def test_skip_when_threads_exist_but_no_prior_copilot_review(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            head_sha="head123",
            copilot_review_id=0,
            unresolved_threads=2,
            reviews=[
                ReviewInfo(id=10, user="alice", state="CHANGES_REQUESTED", commit_sha="old123"),
            ],
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert result.preconditions.get("stuck_prior_threads") is False

    def test_execute_when_commented_review_inline_count_unknown(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            active_session=False,
            review_state="COMMENTED",
            copilot_review_id=100,
            copilot_review_inline_count=-1,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_skip_when_ci_pending_even_if_review_actionable(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="pending",
            active_session=False,
            review_state="COMMENTED",
            copilot_review_id=100,
            copilot_review_inline_count=1,
        )
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "pending" in result.details.lower()

    def test_execute_dispatches_repair(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="failing",
            head_sha="abc123",
            copilot_review_id=0,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.dispatch_repair.return_value = 999

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)
            assert result.decision == ActionDecision.EXECUTE
            provider.dispatch_repair.assert_called_once()

    def test_execute_uses_ci_only_dedup_limit_of_one(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="failing",
            head_sha="abc123",
            copilot_review_id=0,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.dispatch_repair.return_value = 999

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ) as mock_check_deduplication,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        mock_check_deduplication.assert_called_once_with(provider, 42, "abc123", max_dispatches=1)

    def test_execute_uses_default_dedup_limit_when_review_actionable(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=12,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_review_comments.return_value = [MagicMock(id=1)]
        provider.dispatch_repair.return_value = 77

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ) as mock_check_deduplication,
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        mock_check_deduplication.assert_called_once_with(provider, 42, "abc123")

    def test_skip_when_dedup_limit_reached(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="failing", head_sha="abc123")
        derived = DerivedState(snapshot)
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
            return_value=(True, 3),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)
            assert result.decision == ActionDecision.SKIP
            assert "dedup" in result.details.lower()
            assert result.limit_reached is True

    def test_skip_when_cycle_limit_reached(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="failing", head_sha="abc123")
        derived = DerivedState(snapshot)
        provider = MagicMock()

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(True, 5),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)
            assert result.decision == ActionDecision.SKIP
            assert "cycle" in result.details.lower()
            assert result.limit_reached is True

    def test_failed_checks_uses_actionable_subset_only(self) -> None:
        """execute() passes only actionable failed checks to dispatch_repair."""
        from agentic_devtools.cli.ci.models import CheckRunStatus

        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="failing",
            ci_failed_checks=["Targeted Checks ✅"],
            head_sha="abc123",
            check_runs=[
                CheckRunStatus(id=1, name="Targeted Checks ✅", status="completed", conclusion="failure"),
                CheckRunStatus(id=2, name="flaky-optional", status="completed", conclusion="failure"),
            ],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.dispatch_repair.return_value = 1

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            action.execute(provider, snapshot, derived)

        call_kwargs = provider.dispatch_repair.call_args
        passed_checks = call_kwargs.kwargs.get("failed_checks") or call_kwargs.args[3]
        check_names = [cr.name for cr in passed_checks]
        assert "Targeted Checks ✅" in check_names
        assert "flaky-optional" not in check_names

    def test_execute_sets_repair_dispatched_on_derived(self) -> None:
        """execute() must set derived.repair_dispatched after successful dispatch."""
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="failing",
            head_sha="abc123",
            copilot_review_id=0,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.dispatch_repair.return_value = 999

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)
            assert result.decision == ActionDecision.EXECUTE
            assert derived.repair_dispatched is True

    def test_failed_when_deduplication_check_raises(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="failing", head_sha="abc123")
        derived = DerivedState(snapshot)
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
            side_effect=RuntimeError("dedup boom"),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.FAILED
        assert "Deduplication check failed" in result.details

    def test_failed_when_cycle_limit_check_raises(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, ci_status="failing", head_sha="abc123")
        derived = DerivedState(snapshot)
        provider = MagicMock()

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                side_effect=RuntimeError("cycle boom"),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.FAILED
        assert "Cycle limit check failed" in result.details

    def test_execute_dispatches_review_only_and_fetches_review_comments(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=12,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_review_comments.return_value = [MagicMock(id=1)]
        provider.dispatch_repair.return_value = 77

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        call_kwargs = provider.dispatch_repair.call_args.kwargs
        assert call_kwargs["repair_type"] == "review"
        assert call_kwargs["review_comments"] == [provider.list_review_comments.return_value[0]]

    def test_execute_dispatches_review_for_stuck_prior_threads(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="head123",
            copilot_review_id=0,
            unresolved_threads=2,
            reviews=[
                ReviewInfo(
                    id=11, user="Copilot", state="COMMENTED", commit_sha="old111", submitted_at="2024-01-01T10:00:00Z"
                ),
                ReviewInfo(
                    id=12,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old222",
                    submitted_at="2024-01-01T11:00:00Z",
                ),
            ],
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        review_comment_a = MagicMock(id=101)
        review_comment_b = MagicMock(id=102)
        review_comment_b_duplicate = MagicMock(id=102)
        review_comment_suppressed_a = MagicMock(id=-1)
        review_comment_suppressed_b = MagicMock(id=-1)
        provider.list_review_comments.side_effect = [
            [review_comment_b, review_comment_suppressed_a],
            [review_comment_a, review_comment_b_duplicate, review_comment_suppressed_b],
        ]
        provider.dispatch_repair.return_value = 88

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        call_kwargs = provider.dispatch_repair.call_args.kwargs
        assert call_kwargs["repair_type"] == "review"
        assert call_kwargs["review_id"] == 12
        assert call_kwargs["review_comments"] == [
            review_comment_b,
            review_comment_suppressed_a,
            review_comment_a,
            review_comment_suppressed_b,
        ]
        provider.list_review_comments.assert_any_call(42, 12)
        provider.list_review_comments.assert_any_call(42, 11)

    def test_execute_stuck_prior_threads_uses_stable_order_for_missing_or_invalid_timestamps(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="head123",
            copilot_review_id=0,
            unresolved_threads=2,
            reviews=[
                ReviewInfo(id=11, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old111", submitted_at=""),
                ReviewInfo(
                    id=12,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old222",
                    submitted_at=None,  # type: ignore[arg-type]
                ),
                ReviewInfo(
                    id=13,
                    user="Copilot",
                    state="CHANGES_REQUESTED",
                    commit_sha="old333",
                    submitted_at=123,  # type: ignore[arg-type]
                ),
            ],
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_review_comments.return_value = []
        provider.dispatch_repair.return_value = 89

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        call_kwargs = provider.dispatch_repair.call_args.kwargs
        assert call_kwargs["review_id"] == 13

    def test_execute_skips_stuck_threads_when_review_id_dedup_matches_prior_review(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="head123",
            copilot_review_id=0,
            unresolved_threads=2,
            reviews=[
                ReviewInfo(id=12, user="Copilot", state="CHANGES_REQUESTED", commit_sha="old222"),
            ],
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
            return_value=True,
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "review_id=12" in result.details
        provider.dispatch_repair.assert_not_called()

    def test_execute_continues_when_review_comments_fetch_fails(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=12,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_review_comments.side_effect = RuntimeError("comments boom")
        provider.dispatch_repair.return_value = 88

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        assert provider.dispatch_repair.call_args.kwargs["review_comments"] == []

    def test_failed_when_dispatch_repair_raises(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="failing",
            head_sha="abc123",
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.dispatch_repair.side_effect = RuntimeError("dispatch boom")

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.FAILED
        assert "dispatch_repair call failed" in result.details

    def test_execute_dispatches_both_when_ci_failing_and_review_actionable(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="failing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=12,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_review_comments.return_value = [MagicMock(id=1)]
        provider.dispatch_repair.return_value = 99

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        assert provider.dispatch_repair.call_args.kwargs["repair_type"] == "both"

    def test_execute_when_duplicate_trigger_exists_for_review_id(self) -> None:
        """FR-012: Duplicate trigger for same review_id is treated as already dispatched."""
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=4401589029,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()

        with patch(
            "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
            return_value=True,
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "review_id=4401589029" in result.details
        assert getattr(derived, "repair_dispatched", False) is False
        provider.dispatch_repair.assert_not_called()

    def test_execute_when_review_id_dedup_check_raises_fail_open(self) -> None:
        """Review-ID dedup check failure proceeds fail-open (dispatches anyway)."""
        snapshot = PRStateSnapshot(
            pr_number=42,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.list_review_comments.return_value = []
        provider.dispatch_repair.return_value = 200

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                side_effect=RuntimeError("API error"),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        provider.dispatch_repair.assert_called_once()

    def test_exclusion_context_filters_review_comments(self) -> None:
        """ExclusionContext filters out already-applied comments from dispatch."""
        from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext

        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="failing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=3,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        exclusion_ctx = ExclusionContext(resolved_comment_ids={101, 102})
        derived.set("exclusion_context", exclusion_ctx)

        provider = MagicMock()
        provider.list_review_comments.return_value = [
            MagicMock(id=101),
            MagicMock(id=102),
            MagicMock(id=103),
        ]
        provider.dispatch_repair.return_value = 999

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        call_kwargs = provider.dispatch_repair.call_args
        review_comments = call_kwargs.kwargs.get("review_comments") or call_kwargs[0][4]
        assert len(review_comments) == 1

    def test_exclusion_context_skips_repair_when_all_excluded_ci_passing(self) -> None:
        """SKIP when all review comments excluded and CI is passing."""
        from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext

        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        exclusion_ctx = ExclusionContext(resolved_comment_ids={101, 102})
        derived.set("exclusion_context", exclusion_ctx)

        provider = MagicMock()
        provider.list_review_comments.return_value = [
            MagicMock(id=101),
            MagicMock(id=102),
        ]

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.SKIP
        assert "auto-applied" in result.details.lower()

    def test_exclusion_context_no_matching_ids_still_dispatches(self) -> None:
        """Dispatch when exclusion context IDs don't match any review comments."""
        from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext

        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="passing",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        # Exclusion context has IDs that don't match actual review comments
        exclusion_ctx = ExclusionContext(resolved_comment_ids={999, 998})
        derived.set("exclusion_context", exclusion_ctx)

        provider = MagicMock()
        provider.list_review_comments.return_value = [
            MagicMock(id=101),
            MagicMock(id=102),
        ]
        provider.dispatch_repair.return_value = 999

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE

    def test_exclusion_context_does_not_skip_when_ci_unknown(self) -> None:
        """Do not SKIP on unknown CI status even when all review comments are excluded."""
        from agentic_devtools.cli.ci.pipeline.exclusion import ExclusionContext

        snapshot = PRStateSnapshot(
            pr_number=1,
            ci_status="unknown",
            head_sha="abc123",
            review_state="CHANGES_REQUESTED",
            copilot_review_id=100,
            copilot_review_inline_count=2,
            check_runs=[],
        )
        derived = DerivedState(snapshot)
        exclusion_ctx = ExclusionContext(resolved_comment_ids={101, 102})
        derived.set("exclusion_context", exclusion_ctx)

        provider = MagicMock()
        provider.list_review_comments.return_value = [
            MagicMock(id=101),
            MagicMock(id=102),
        ]
        provider.dispatch_repair.return_value = 999

        with (
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.is_duplicate_trigger",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_deduplication",
                return_value=(False, 0),
            ),
            patch(
                "agentic_devtools.cli.ci.pipeline.actions.dispatch_repair.check_cycle_limit",
                return_value=(False, 1),
            ),
        ):
            action = DispatchRepairAction()
            result = action.execute(provider, snapshot, derived)

        assert result.decision == ActionDecision.EXECUTE
        provider.dispatch_repair.assert_called_once()
