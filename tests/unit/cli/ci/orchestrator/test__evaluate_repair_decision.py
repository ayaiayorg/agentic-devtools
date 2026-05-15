"""Tests for _evaluate_repair_decision() in the orchestrator."""

from agentic_devtools.cli.ci.models import CheckRunStatus
from agentic_devtools.cli.ci.orchestrator import _evaluate_repair_decision


class TestEvaluateRepairDecision:
    """Tests for the repair decision evaluation logic."""

    def test_no_issues_returns_no_repair(self) -> None:
        decision = _evaluate_repair_decision(
            any_failed=False,
            has_changes_requested=False,
            copilot_review_id=0,
            failed_checks=[],
        )
        assert decision.repair_needed is False
        assert decision.repair_type == ""

    def test_review_only_returns_review_type(self) -> None:
        """FR-001: Detect actionable review comments and set repair_type='review'."""
        decision = _evaluate_repair_decision(
            any_failed=False,
            has_changes_requested=True,
            copilot_review_id=100,
            failed_checks=[],
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "review"
        assert decision.review_id == 100

    def test_ci_only_returns_ci_type(self) -> None:
        """FR-002: Detect failing CI checks and set repair_type='ci'."""
        failed = [CheckRunStatus(id=1, name="ci/test", status="completed", conclusion="failure")]
        decision = _evaluate_repair_decision(
            any_failed=True,
            has_changes_requested=False,
            copilot_review_id=0,
            failed_checks=failed,
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "ci"
        assert decision.failed_checks == failed

    def test_both_returns_both_type(self) -> None:
        """When both review and CI issues exist, repair_type='both'."""
        failed = [CheckRunStatus(id=1, name="lint", status="completed", conclusion="failure")]
        decision = _evaluate_repair_decision(
            any_failed=True,
            has_changes_requested=True,
            copilot_review_id=200,
            failed_checks=failed,
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "both"
        assert decision.review_id == 200
        assert decision.failed_checks == failed

    def test_review_without_copilot_id(self) -> None:
        """Changes requested by non-Copilot reviewer still triggers repair."""
        decision = _evaluate_repair_decision(
            any_failed=False,
            has_changes_requested=True,
            copilot_review_id=0,
            failed_checks=[],
        )
        assert decision.repair_needed is True
        assert decision.repair_type == "review"
        assert decision.review_id == 0
