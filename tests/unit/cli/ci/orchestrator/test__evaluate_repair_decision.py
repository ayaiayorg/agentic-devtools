"""Tests for _evaluate_repair_decision() in the orchestrator."""

from agentic_devtools.cli.ci.models import CheckRunStatus
from agentic_devtools.cli.ci.orchestrator import _evaluate_repair_decision


class TestEvaluateRepairDecision:
    """Tests for the repair decision evaluation logic."""

    def test_no_issues_returns_no_repair(self) -> None:
        decision = _evaluate_repair_decision(
            any_failed=False,
            copilot_actionable_review=False,
            copilot_review_id=0,
            copilot_review_comments=[],
            failed_checks=[],
        )
        assert decision.repair_needed is False
        assert decision.repair_type == ""

    def test_review_only_returns_review_type(self) -> None:
        """FR-001: Copilot CHANGES_REQUESTED state triggers repair_type='review'."""
        decision = _evaluate_repair_decision(
            any_failed=False,
            copilot_actionable_review=True,
            copilot_review_id=100,
            copilot_review_comments=[],
            failed_checks=[],
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "review"
        assert decision.review_id == 100

    def test_review_comments_stored_in_decision(self) -> None:
        """Pre-fetched review comments are stored in RepairDecision."""
        comments = ["Please fix the null check", "Use const instead of let"]
        decision = _evaluate_repair_decision(
            any_failed=False,
            copilot_actionable_review=True,
            copilot_review_id=100,
            copilot_review_comments=comments,
            failed_checks=[],
        )
        assert decision.repair_needed is True
        assert decision.review_comments == tuple(comments)

    def test_ci_only_returns_ci_type(self) -> None:
        """FR-002: Detect failing CI checks and set repair_type='ci'."""
        failed = [CheckRunStatus(id=1, name="ci/test", status="completed", conclusion="failure")]
        decision = _evaluate_repair_decision(
            any_failed=True,
            copilot_actionable_review=False,
            copilot_review_id=0,
            copilot_review_comments=[],
            failed_checks=failed,
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "ci"
        assert decision.failed_checks == tuple(failed)

    def test_both_returns_both_type(self) -> None:
        """When both review and CI issues exist, repair_type='both'."""
        failed = [CheckRunStatus(id=1, name="lint", status="completed", conclusion="failure")]
        decision = _evaluate_repair_decision(
            any_failed=True,
            copilot_actionable_review=True,
            copilot_review_id=200,
            copilot_review_comments=[],
            failed_checks=failed,
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "both"
        assert decision.review_id == 200
        assert decision.failed_checks == tuple(failed)

    def test_non_copilot_review_does_not_trigger_repair(self) -> None:
        """Human CHANGES_REQUESTED reviews should not trigger repair dispatch."""
        decision = _evaluate_repair_decision(
            any_failed=False,
            copilot_actionable_review=False,
            copilot_review_id=0,
            copilot_review_comments=[],
            failed_checks=[],
        )
        assert decision.repair_needed is False
