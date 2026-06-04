"""Tests for DispatchRepairAction."""

from unittest.mock import MagicMock, patch

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
