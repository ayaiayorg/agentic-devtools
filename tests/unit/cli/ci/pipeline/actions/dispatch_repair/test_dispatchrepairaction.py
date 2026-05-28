"""Tests for DispatchRepairAction."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.ci.pipeline.actions.dispatch_repair import DispatchRepairAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestDispatchRepairAction:
    """Tests for dispatch repair action evaluation."""

    def test_skip_when_active_session(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, active_session=True, ci_status="failing")
        derived = DerivedState(snapshot)
        action = DispatchRepairAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "active" in result.details.lower()

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
            ci_failed_checks=["Tests ✅"],
            head_sha="abc123",
            check_runs=[
                CheckRunStatus(id=1, name="Tests ✅", status="completed", conclusion="failure"),
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
        assert "Tests ✅" in check_names
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
