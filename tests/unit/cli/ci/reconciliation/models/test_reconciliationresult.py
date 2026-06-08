"""Tests for ReconciliationResult dataclass."""

from agentic_devtools.cli.ci.reconciliation.models import (
    ReconciliationAction,
    ReconciliationResult,
    WorkflowRun,
)


class TestReconciliationResult:
    """Tests for ReconciliationResult dataclass."""

    def test_no_action_result(self) -> None:
        """ReconciliationResult with NO_ACTION and no run."""
        result = ReconciliationResult(
            action=ReconciliationAction.NO_ACTION,
            message="No retriable runs found.",
        )
        assert result.action == ReconciliationAction.NO_ACTION
        assert result.run is None
        assert result.message == "No retriable runs found."
        assert result.context is None

    def test_retried_result_with_run(self) -> None:
        """ReconciliationResult with RETRIED action includes a run."""
        run = WorkflowRun(
            id=42,
            name="build",
            conclusion="failure",
            run_attempt=1,
            created_at="2024-01-15T10:00:00Z",
            event="push",
            head_branch="main",
        )
        result = ReconciliationResult(
            action=ReconciliationAction.RETRIED,
            run=run,
            message="Retried run 42.",
        )
        assert result.action == ReconciliationAction.RETRIED
        assert result.run is run
        assert result.run.id == 42

    def test_reconciliation_action_values(self) -> None:
        """ReconciliationAction enum has expected values."""
        assert ReconciliationAction.RETRIED.value == "retried"
        assert ReconciliationAction.ESCALATED.value == "escalated"
        assert ReconciliationAction.NO_ACTION.value == "no_action"
